from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.deps import close_redis
from app.routers import health, auth, users, workspaces, members, datasets, documents, providers, retrieval, chat, workflows, apps, student_auth, students
from app.seed import seed_super_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hooks."""
    # -- Startup --
    await seed_super_admin()
    yield
    # -- Shutdown --
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow web dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(workspaces.router)
app.include_router(members.router)
app.include_router(datasets.router)
app.include_router(documents.router)
app.include_router(providers.router)
app.include_router(retrieval.router)
app.include_router(chat.router)
app.include_router(workflows.router)
app.include_router(apps.router)
app.include_router(student_auth.router)
app.include_router(students.router)
