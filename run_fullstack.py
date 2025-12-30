"""Run the full-stack application with SvelteKit frontend and FastAPI backend."""
import os
import uvicorn
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from src.api.app import app

# Path to the built SvelteKit frontend
FRONTEND_BUILD_DIR = Path(__file__).parent / "frontend" / "build"

# Serve SvelteKit static files (using node adapter output)
if FRONTEND_BUILD_DIR.exists():
    # SvelteKit node adapter creates a 'client' directory with static assets
    client_dir = FRONTEND_BUILD_DIR / "client"

    if client_dir.exists():
        # Mount static assets (_app directory contains JS/CSS bundles)
        immutable_dir = client_dir / "_app" / "immutable"
        if immutable_dir.exists():
            app.mount(
                "/_app/immutable",
                StaticFiles(directory=str(immutable_dir)),
                name="immutable-assets"
            )

        version_dir = client_dir / "_app" / "version.json"
        if version_dir.exists():
            @app.get("/_app/version.json")
            async def serve_version():
                return FileResponse(version_dir)

        # Serve other static files (images, fonts, etc.)
        @app.get("/{file_path:path}")
        async def serve_static_or_page(file_path: str):
            """Serve static files or SvelteKit-rendered pages."""
            # Skip API routes
            if file_path.startswith("api/") or file_path.startswith("docs") or file_path.startswith("openapi"):
                return None  # Let FastAPI handle these

            # Root path - serve index.html
            if not file_path:
                index_html = client_dir / "index.html"
                if index_html.exists():
                    return FileResponse(index_html)

            # Try to find the file in client directory
            full_path = client_dir / file_path

            # Serve static file if it exists
            if full_path.is_file():
                return FileResponse(full_path)

            # For routes, try the prerendered HTML
            # SvelteKit creates HTML files for each route
            if file_path.endswith("/"):
                html_path = client_dir / file_path / "index.html"
            else:
                html_path = client_dir / file_path
                if not html_path.suffix:
                    html_path = client_dir / file_path / "index.html"

            if html_path.exists() and html_path.is_file():
                return FileResponse(html_path)

            # Final fallback: root index.html for client-side routing
            index_html = client_dir / "index.html"
            if index_html.exists():
                return FileResponse(index_html)

            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not found")

        print(f"✅ Serving SvelteKit frontend from: {client_dir}")
    else:
        print(f"⚠️  SvelteKit client directory not found at: {client_dir}")
else:
    print("⚠️  Frontend build directory not found. Run 'cd frontend && npm run build' first.")

    @app.get("/")
    async def root():
        return {
            "message": "UFE Research Writer API",
            "frontend": "not built - run 'cd frontend && npm run build'",
            "api_docs": "/docs"
        }


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(
        "run_fullstack:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
