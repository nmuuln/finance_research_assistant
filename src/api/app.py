"""Enhanced FastAPI application with session management and file uploads."""
import os
import uuid
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.database import Database
from src.tools.file_processor import FileProcessor, summarize_file_content
from src.pipeline import run_pipeline, run_literature_review_phase, run_pipeline_with_literature
from src.llm.writer_agent import draft_finance_report, init_gemini_client
from src.tools.output_formatter import OutputFormatterTool
from src.utils.spaces import get_spaces_client
from src.research.literature_review import LiteratureReview, format_literature_review_for_display
from dotenv import load_dotenv
import json

# ADK Agent integration
from google.adk import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai.types import Content, Part
from src.adk_app.agent import build_agent

load_dotenv()

app = FastAPI(title="UFE Research Writer API")

# Initialize ADK agent
adk_session_service = InMemorySessionService()
adk_agent = build_agent()
adk_runner = Runner(
    app_name="ufe_research",
    agent=adk_agent,
    session_service=adk_session_service,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
db = Database(db_path=os.getenv("DATABASE_PATH", "data/app.db"))

# File storage
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# Request/Response Models
class SessionCreate(BaseModel):
    topic: Optional[str] = None
    language: str = "mn"


class SessionResponse(BaseModel):
    id: str
    created_at: str
    updated_at: str
    topic: Optional[str]
    language: str
    status: str


class ChatMessage(BaseModel):
    message: str
    language: Optional[str] = None


class ResearchRequest(BaseModel):
    topic: str
    language: str = "mn"
    use_uploaded_files: bool = True


class ReportRequest(BaseModel):
    topic: str
    research_brief: str
    references: str
    language: str = "mn"


class LiteratureReviewRequest(BaseModel):
    topic: str
    max_papers_per_source: int = 5


class LiteratureReviewApproval(BaseModel):
    approved: bool
    modifications: Optional[str] = None


class ResearchWithLiteratureRequest(BaseModel):
    topic: str
    language: str = "mn"
    use_uploaded_files: bool = True


# Session Endpoints
@app.post("/api/sessions", response_model=SessionResponse)
async def create_session(session_data: SessionCreate):
    """Create a new research session."""
    session_id = str(uuid.uuid4())
    session = db.create_session(
        session_id=session_id,
        topic=session_data.topic,
        language=session_data.language
    )
    return session


@app.get("/api/sessions")
async def list_sessions(limit: int = 50, offset: int = 0):
    """List all sessions with pagination."""
    sessions = db.list_sessions(limit=limit, offset=offset)
    return {"sessions": sessions, "limit": limit, "offset": offset}


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Include related data
    artifacts = db.list_artifacts(session_id)
    files = db.list_uploaded_files(session_id)
    messages = db.get_messages(session_id)

    return {
        "session": session,
        "artifacts": artifacts,
        "files": files,
        "messages": messages
    }


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and all related data."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # SQLite cascade will handle deletion of related records
    db.update_session(session_id, status="deleted")
    return {"message": "Session deleted successfully"}


# File Upload Endpoints
@app.post("/api/sessions/{session_id}/upload")
async def upload_file(session_id: str, file: UploadFile = File(...)):
    """Upload a file to a session."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Validate file type
    if not FileProcessor.is_supported(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported: PDF, CSV, Excel"
        )

    # Read file content
    file_id = str(uuid.uuid4())
    file_ext = Path(file.filename).suffix
    storage_filename = f"{file_id}{file_ext}"
    content = await file.read()

    # Try to upload to Spaces first, fall back to local storage
    spaces_client = get_spaces_client()
    storage_path: str = ""
    file_url: Optional[str] = None

    if spaces_client:
        # Upload to DigitalOcean Spaces
        try:
            object_key = f"uploads/{session_id}/{storage_filename}"
            file_url = spaces_client.upload_file(
                file_content=content,
                object_key=object_key,
                content_type=file.content_type,
                make_public=False  # Keep files private
            )
            storage_path = f"spaces://{object_key}"  # Store as Spaces reference
            print(f"✅ File uploaded to Spaces: {file_url}")
        except Exception as e:
            print(f"⚠️ Spaces upload failed, falling back to local storage: {e}")
            spaces_client = None  # Fall back to local

    if not spaces_client:
        # Fall back to local filesystem storage
        local_path = UPLOAD_DIR / session_id
        local_path.mkdir(parents=True, exist_ok=True)
        file_path = local_path / storage_filename

        with open(file_path, "wb") as f:
            f.write(content)

        storage_path = str(file_path)
        file_url = None  # No public URL for local files
        print(f"📁 File saved locally: {storage_path}")

    # Record in database
    file_type = FileProcessor.get_file_type(file.filename) or "application/octet-stream"
    file_record = db.create_uploaded_file(
        session_id=session_id,
        filename=file.filename,
        file_type=file_type,
        storage_path=storage_path,
        file_size=len(content)
    )

    # Add file_url to metadata if it exists
    if file_url:
        file_record['file_url'] = file_url

    # Process file asynchronously
    try:
        # If stored in Spaces, download to temp location for processing
        if storage_path.startswith("spaces://") and spaces_client is not None:
            # Create temporary file for processing
            temp_dir = Path("data/temp")
            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_path = temp_dir / storage_filename

            # Download from Spaces
            object_key = storage_path.replace("spaces://", "")
            spaces_client.download_to_path(object_key, str(temp_path))
            process_path = str(temp_path)
        else:
            # Use local path directly
            process_path = storage_path

        result = FileProcessor.process_file(process_path)

        # Clean up temp file if used
        if storage_path.startswith("spaces://"):
            Path(process_path).unlink(missing_ok=True)

        if result['success']:
            db.update_uploaded_file(
                file_record['id'],
                processed=True,
                extracted_content=result['content'],
                metadata=result.get('metadata', {})
            )
            file_record['processed'] = True
            file_record['extraction_success'] = True
        else:
            db.update_uploaded_file(
                file_record['id'],
                processed=True,
                metadata={'error': result.get('error')}
            )
            file_record['processed'] = True
            file_record['extraction_success'] = False
            file_record['error'] = result.get('error')
    except Exception as e:
        file_record['extraction_error'] = str(e)

    return file_record


@app.get("/api/sessions/{session_id}/files")
async def list_files(session_id: str):
    """List all uploaded files for a session."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    files = db.list_uploaded_files(session_id)
    return {"files": files}


# Research Endpoints
@app.post("/api/sessions/{session_id}/research")
async def run_research(session_id: str, request: ResearchRequest):
    """Run research for a session."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Update session topic
    db.update_session(session_id, topic=request.topic, language=request.language)

    # Get uploaded file content if requested
    additional_context = ""
    if request.use_uploaded_files:
        files = db.list_uploaded_files(session_id)
        processed_files = [f for f in files if f.get('processed')]

        if processed_files:
            context_parts = ["=== Uploaded Reference Materials ===\n"]
            for file in processed_files:
                if file.get('extracted_content'):
                    context_parts.append(f"\n--- {file['filename']} ---")
                    # Summarize to avoid token overflow
                    summary = summarize_file_content(file['extracted_content'], max_chars=3000)
                    context_parts.append(summary)

            additional_context = "\n".join(context_parts)

    # Run research pipeline
    try:
        from src.pipeline import run_pipeline

        result = run_pipeline(
            topic=request.topic,
            language=request.language,
            additional_context=additional_context
        )

        if result.get('success'):
            # Store as metadata in session
            db.update_session(
                session_id,
                metadata={
                    'research_brief': result.get('brief'),
                    'references': result.get('references'),
                    'context_used': bool(additional_context)
                }
            )

            return {
                "success": True,
                "brief": result.get('brief'),
                "references": result.get('references'),
                "preview": result.get('preview')
            }
        else:
            raise HTTPException(status_code=500, detail=result.get('error', 'Research failed'))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Research error: {str(e)}")


# Literature Review Endpoints
@app.post("/api/sessions/{session_id}/literature-review")
async def start_literature_review(session_id: str, request: LiteratureReviewRequest):
    """
    Phase 1: Run literature review for a topic.
    Returns academic papers and synthesis for user approval.
    """
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        result = run_literature_review_phase(
            topic=request.topic,
            max_papers_per_source=request.max_papers_per_source,
        )

        # Store in session metadata
        current_metadata = {}
        if session.get("metadata"):
            try:
                current_metadata = json.loads(session["metadata"]) if isinstance(session["metadata"], str) else session["metadata"]
            except (json.JSONDecodeError, TypeError):
                current_metadata = {}

        current_metadata["literature_review"] = result.get("review")
        current_metadata["literature_review_status"] = "pending_approval"

        db.update_session(
            session_id,
            topic=request.topic,
            metadata=current_metadata
        )

        return {
            "success": True,
            "review": result.get("review"),
            "formatted": result.get("formatted"),
            "paper_count": result.get("paper_count"),
            "requires_approval": True,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Literature review error: {str(e)}")


@app.post("/api/sessions/{session_id}/literature-review/approve")
async def approve_literature_review(session_id: str, approval: LiteratureReviewApproval):
    """
    Approve or reject the literature review before continuing research.
    """
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get existing metadata
    metadata = {}
    if session.get("metadata"):
        try:
            metadata = json.loads(session["metadata"]) if isinstance(session["metadata"], str) else session["metadata"]
        except (json.JSONDecodeError, TypeError):
            metadata = {}

    if "literature_review" not in metadata:
        raise HTTPException(status_code=400, detail="No literature review to approve. Run /literature-review first.")

    if approval.approved:
        metadata["literature_review"]["approved"] = True
        metadata["literature_review_status"] = "approved"
    else:
        metadata["literature_review_status"] = "rejected"

    if approval.modifications:
        metadata["literature_review"]["user_modifications"] = approval.modifications

    db.update_session(session_id, metadata=metadata)

    return {
        "success": True,
        "status": metadata["literature_review_status"],
        "can_proceed": approval.approved,
    }


@app.post("/api/sessions/{session_id}/research-with-literature")
async def run_research_with_lit(session_id: str, request: ResearchWithLiteratureRequest):
    """
    Phase 2: Run full research pipeline with approved literature review.
    """
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get approved literature review from metadata
    metadata = {}
    if session.get("metadata"):
        try:
            metadata = json.loads(session["metadata"]) if isinstance(session["metadata"], str) else session["metadata"]
        except (json.JSONDecodeError, TypeError):
            metadata = {}

    lit_review = metadata.get("literature_review")
    if not lit_review:
        raise HTTPException(
            status_code=400,
            detail="No literature review found. Run /literature-review first."
        )

    if not lit_review.get("approved"):
        raise HTTPException(
            status_code=400,
            detail="Literature review must be approved before proceeding. Call /literature-review/approve first."
        )

    # Get uploaded file content if requested
    additional_context = ""
    if request.use_uploaded_files:
        files = db.list_uploaded_files(session_id)
        processed_files = [f for f in files if f.get('processed')]

        if processed_files:
            context_parts = ["=== Uploaded Reference Materials ===\n"]
            for file in processed_files:
                if file.get('extracted_content'):
                    context_parts.append(f"\n--- {file['filename']} ---")
                    summary = summarize_file_content(file['extracted_content'], max_chars=3000)
                    context_parts.append(summary)

            additional_context = "\n".join(context_parts)

    try:
        result = run_pipeline_with_literature(
            topic=request.topic,
            literature_review_data=lit_review,
            language=request.language,
            additional_context=additional_context,
        )

        if result.get('success'):
            # Update session metadata with research results
            metadata['research_brief'] = result.get('brief')
            metadata['references'] = result.get('references')
            metadata['literature_included'] = result.get('literature_included')

            db.update_session(session_id, metadata=metadata)

            return {
                "success": True,
                "brief": result.get('brief'),
                "references": result.get('references'),
                "preview": result.get('preview'),
                "literature_included": result.get('literature_included'),
                "literature_paper_count": result.get('literature_paper_count'),
            }
        else:
            raise HTTPException(status_code=500, detail="Research with literature failed")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Research error: {str(e)}")


@app.post("/api/sessions/{session_id}/report")
async def generate_report_endpoint(session_id: str, request: ReportRequest):
    """Generate a thesis-style report."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        # Load prompts
        from pathlib import Path
        base = Path(__file__).parent.parent
        domain_guard = (base / "prompts" / "domain_guard.txt").read_text(encoding="utf-8")
        writer_tone = (base / "prompts" / "writer_tone.txt").read_text(encoding="utf-8")
        writer_structure = (base / "prompts" / "writer_structure.txt").read_text(encoding="utf-8")

        # Initialize Gemini client
        from src.config import cfg
        c = cfg()
        gemini = init_gemini_client(c["GOOGLE_API_KEY"])

        # Parse references
        refs_list = request.references.split('\n') if isinstance(request.references, str) else request.references

        # Generate report using writer agent
        report = draft_finance_report(
            client=gemini,
            domain_guard=domain_guard,
            tone=writer_tone,
            structure=writer_structure,
            research_question=request.topic,
            brief=request.research_brief,
            references=refs_list,
            language=request.language
        )

        if report:
            # Export to docx
            formatter = OutputFormatterTool()
            export_result = formatter(
                report,
                out_dir="data/outputs",
                filename_prefix=f"{session_id}_{request.topic[:30]}"
            )

            # Upload to Spaces if configured
            spaces_client = get_spaces_client()
            file_url = export_result.get('url')  # Default to local path/URL

            if spaces_client and export_result.get('filepath'):
                try:
                    # Upload the generated .docx file to Spaces
                    local_file_path = export_result['filepath']
                    filename = Path(local_file_path).name
                    object_key = f"reports/{session_id}/{filename}"

                    file_url = spaces_client.upload_file_from_path(
                        file_path=local_file_path,
                        object_key=object_key,
                        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        make_public=True  # Make reports publicly downloadable
                    )

                    print(f"✅ Report uploaded to Spaces: {file_url}")

                    # Optionally delete local file after upload to save space
                    # Path(local_file_path).unlink(missing_ok=True)

                except Exception as e:
                    print(f"⚠️ Spaces upload failed for report, using local file: {e}")
                    # Keep using local file_url from export_result

            # Create artifact record
            artifact = db.create_artifact(
                session_id=session_id,
                title=request.topic,
                content=report,
                research_brief=request.research_brief,
                reference_list=request.references,
                file_url=file_url,  # Spaces URL or local path
                metadata={
                    'language': request.language,
                    'word_count': len(report.split()),
                    'generated_at': datetime.utcnow().isoformat(),
                    'storage': 'spaces' if file_url and file_url.startswith('http') else 'local'
                }
            )

            return {
                "success": True,
                "artifact_id": artifact['id'],
                "report": report,
                "file_url": file_url,
                "download_filename": export_result.get('filename')
            }
        else:
            raise HTTPException(status_code=500, detail="Report generation failed")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report error: {str(e)}")


# Artifact Endpoints
@app.get("/api/sessions/{session_id}/artifacts")
async def list_artifacts(session_id: str):
    """List all artifacts (reports) for a session."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    artifacts = db.list_artifacts(session_id)
    return {"artifacts": artifacts}


@app.get("/api/artifacts/{artifact_id}")
async def get_artifact(artifact_id: int):
    """Get a specific artifact by ID."""
    artifact = db.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    return artifact


# Message Endpoints
@app.post("/api/sessions/{session_id}/messages")
async def save_message(session_id: str, message: dict):
    """Save a message to the session."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    role = message.get("role", "user")
    content = message.get("content", "")
    metadata = message.get("metadata")

    db.add_message(session_id, role=role, content=content, metadata=metadata)

    return {"success": True}


@app.get("/api/sessions/{session_id}/messages")
async def get_messages(session_id: str, limit: int = 100):
    """Get conversation history for a session."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = db.get_messages(session_id, limit=limit)
    return {"messages": messages}


# ADK Agent Chat Endpoint
@app.post("/api/sessions/{session_id}/agent-chat")
async def agent_chat(session_id: str, message: dict):
    """Chat with the ADK agent."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_message = message.get("content", "")

    # Ensure ADK session exists
    user_id = "web-user"
    adk_session = await adk_session_service.get_session(
        app_name="ufe_research",
        user_id=user_id,
        session_id=session_id,
    )
    if adk_session is None:
        await adk_session_service.create_session(
            app_name="ufe_research",
            user_id=user_id,
            session_id=session_id,
        )

    # Create ADK message
    adk_message = Content(
        role="user",
        parts=[Part.from_text(text=user_message)],
    )

    # Run agent and collect response
    assistant_response = ""
    async for event in adk_runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=adk_message,
    ):
        if event.author == "user":
            continue

        # Extract text from event
        if hasattr(event, 'content') and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, 'text') and part.text:
                    assistant_response += part.text

    # Store messages in database
    db.add_message(session_id, role="user", content=user_message)
    db.add_message(session_id, role="assistant", content=assistant_response)

    return {
        "role": "assistant",
        "content": assistant_response,
        "session_id": session_id
    }


# Chat Endpoint (simplified)
@app.post("/api/sessions/{session_id}/chat")
async def chat(session_id: str, message: ChatMessage):
    """Send a message to the session (simplified chat)."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Store user message
    db.add_message(session_id, role="user", content=message.message)

    # Simple response for now - integrate with ADK agent later
    response = {
        "message": "Message received. Use /research and /report endpoints for now.",
        "session_id": session_id
    }

    # Store assistant message
    db.add_message(session_id, role="assistant", content=response["message"])

    return response


# Health check
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
