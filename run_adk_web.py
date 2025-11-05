import asyncio
import os
from typing import Any, Dict, List, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google.adk import Runner
from google.adk.events.event import Event
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai.types import Content, Part
from pydantic import BaseModel, Field

from src.adk_app.agent import build_agent

APP_NAME = "agents"


class ChatRequest(BaseModel):
    user_id: str = Field(default="web-user")
    session_id: str = Field(default="session-1")
    message: str = Field(min_length=1, description="User message content")


class EventPart(BaseModel):
    type: str
    data: Dict[str, Any]


class EventPayload(BaseModel):
    author: str
    is_final: bool
    parts: List[EventPart]
    state_delta: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    events: List[EventPayload]


app = FastAPI(title="UFE Research Writer ADK Web API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_service = InMemorySessionService()
agent = build_agent()
runner = Runner(
    app_name=APP_NAME,
    agent=agent,
    session_service=session_service,
)


def _serialize_part(part) -> EventPart:
    if getattr(part, "text", None):
        return EventPart(type="text", data={"text": part.text})
    if getattr(part, "function_call", None):
        func = part.function_call
        args = getattr(func, "args", None)
        return EventPart(
            type="function_call",
            data={
                "name": func.name,
                "args": args,
            },
        )
    if getattr(part, "function_response", None):
        func_resp = part.function_response
        return EventPart(
            type="function_response",
            data={
                "name": func_resp.name,
                "response": func_resp.response,
            },
        )
    if getattr(part, "thought", None):
        return EventPart(type="thought", data={"thought": part.thought})
    if getattr(part, "thought_signature", None):
        return EventPart(
            type="thought_signature",
            data={"signature": part.thought_signature},
        )
    if getattr(part, "inline_data", None):
        return EventPart(
            type="inline_data",
            data={"mime_type": part.inline_data.mime_type},
        )
    return EventPart(type="unknown", data={"repr": str(part)})


def _serialize_event(event: Event) -> EventPayload:
    parts = []
    if getattr(event, "content", None) and event.content.parts:
        parts = [_serialize_part(p) for p in event.content.parts]
    state_delta = getattr(event.actions, "state_delta", {}) or {}
    return EventPayload(
        author=event.author,
        is_final=event.is_final_response(),
        parts=parts,
        state_delta=state_delta,
    )


async def _ensure_session(user_id: str, session_id: str) -> None:
    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )
    if session is None:
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    await _ensure_session(request.user_id, request.session_id)
    message = Content(
        role="user",
        parts=[Part.from_text(text=request.message)],
    )

    events: List[EventPayload] = []
    async for event in runner.run_async(
        user_id=request.user_id,
        session_id=request.session_id,
        new_message=message,
    ):
        if event.author == "user":
            continue
        events.append(_serialize_event(event))
    return ChatResponse(events=events)


class SessionRequest(BaseModel):
    user_id: str = Field(default="web-user")
    session_id: Optional[str] = None
    state: Dict[str, Any] = Field(default_factory=dict)


class SessionResponse(BaseModel):
    session_id: str


@app.post("/sessions", response_model=SessionResponse)
async def create_session(request: SessionRequest) -> SessionResponse:
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=request.user_id,
        session_id=request.session_id,
        state=request.state,
    )
    return SessionResponse(session_id=session.id)


@app.get("/healthz")
async def healthcheck():
    return {"status": "ok"}


def main():
    load_dotenv()
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "run_adk_web:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()

