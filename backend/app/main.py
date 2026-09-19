"""
FastAPI application entry point.

Lifespan:
  - Creates DB tables (SQLAlchemy)
  - Sets up LangGraph Postgres checkpointer
  - Compiles the graph and stores it on app.state
  - Serves uploaded files as static assets
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config import settings
from app.models.database import init_db
from app.graph.workflow import create_compiled_graph
from app.api.routes import documents, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    print("🚀 Aegis HR starting up...")

    # 1. Create application tables
    await init_db()
    print("✅ Database tables ready")

    # 2. Create LangGraph checkpointer and compile graph
    async with AsyncPostgresSaver.from_conn_string(settings.postgres_uri_sync) as checkpointer:
        await checkpointer.setup()  # creates LangGraph checkpoint tables
        compiled_graph = await create_compiled_graph(checkpointer)
        app.state.graph = compiled_graph
        print("✅ LangGraph graph compiled with Postgres checkpointer")

        yield  # App is running

    # ── Shutdown ──────────────────────────────────────────────────────────────
    print("🛑 Aegis HR shutting down")


app = FastAPI(
    title="Aegis HR — Background Verification API",
    description=(
        "Agentic BGV pipeline: OCR → PII masking → LLM extraction → "
        "rule-based evaluation → human-in-the-loop review.\n\n"
        "Developer: Aarushi Sharma | Roll No: 2301010185"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files (uploaded documents) ────────────────────────────────────────
uploads_path = Path(settings.upload_dir)
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(documents.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Aegis HR BGV API"}


@app.get("/")
async def root():
    return {
        "service": "Aegis HR — Background Verification System",
        "developer": "Aarushi Sharma",
        "roll_no": "2301010185",
        "docs": "/docs",
    }
