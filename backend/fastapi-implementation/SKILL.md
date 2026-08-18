---
name: fastapi-implementation
description: >-
  Production guidelines and code patterns for implementing FastAPI backends,
  including clean architecture, routers, Pydantic v2 schemas, SQLAlchemy 2.x
  repositories and async sessions, dependency injection, async patterns,
  pagination, caching, middleware, background tasks, lifespans, and feature workflows.
  Use when building, refactoring, or extending FastAPI services and endpoints.
---

# FastAPI Implementation Skill

## 1. Role & Core Philosophy

You are an expert **FastAPI backend engineer** responsible for implementing production-grade FastAPI applications with clean architecture, strict type safety, asynchronous performance, and maintainable layered design.

### Core Implementation Principles
- **Simple → Typed → Validated → Versioned → Secure → Testable → Observable → Production-Ready**
- Always prefer simple, maintainable solutions over unnecessary abstraction.
- Keep route handlers thin; encapsulate business logic in services and database queries in repositories.
- Never block the asyncio event loop.

---

## 2. Technology Standards

Unless an existing project specifies otherwise, standard stack includes:

* **Python**: 3.11+
* **Framework**: FastAPI
* **Validation & Settings**: Pydantic v2 & `pydantic-settings`
* **ORM & Database**: SQLAlchemy 2.x (Async) + `asyncpg` (PostgreSQL)
* **Migrations**: Alembic
* **HTTP Client**: `httpx` (`httpx.AsyncClient`)
* **Linting & Typing**: Ruff, MyPy / Pyright

> **Dependency Rule**: Inspect existing `pyproject.toml` or `requirements.txt` before adding dependencies. Do not introduce packages if equivalent functionality exists in the project.

---

## 3. Project Structure & Architecture

For medium and large production backends, organize by layer:

```text
app/
├── main.py                     # Application factory and lifespan configuration
├── api/
│   ├── deps.py                 # Common FastAPI dependencies (auth, session, etc.)
│   └── routes/                 # Route handlers organized by domain or version
│       ├── v1/
│       │   ├── __init__.py
│       │   ├── users.py
│       │   ├── tasks.py
│       │   └── auth.py
│       └── v2/
│           ├── __init__.py
│           └── users.py
├── core/
│   ├── config.py               # Pydantic Settings
│   ├── security.py             # Password hashing, JWT utils
│   ├── logging.py              # Structured logging configuration
│   └── exceptions.py           # Domain exceptions
├── db/
│   ├── session.py              # Async engine and session factory
│   └── base.py                 # SQLAlchemy DeclarativeBase
├── models/                     # SQLAlchemy 2.x declarative models
│   ├── user.py
│   └── task.py
├── schemas/                    # Pydantic v2 request/response schemas
│   ├── v1/
│   │   ├── user.py
│   │   └── task.py
│   └── v2/
│       └── user.py
├── repositories/               # Database access layer (queries, CRUD)
│   ├── user.py
│   └── task.py
├── services/                   # Business logic layer
│   ├── auth.py
│   ├── user.py
│   └── task.py
└── tests/
    ├── conftest.py
    └── v1/
        ├── test_users.py
        └── test_tasks.py
```

---

## 4. Application Factory & Lifespan

Keep `main.py` lightweight and use modern FastAPI `lifespan` context managers for resource setup and teardown (database connections, HTTP clients, Redis pools):

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import httpx

from app.api.routes.v1 import auth as auth_v1, tasks as tasks_v1, users as users_v1
from app.core.config import get_settings
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize resources
    settings = get_settings()
    app.state.http_client = httpx.AsyncClient(timeout=10.0)
    yield
    # Shutdown: Cleanly release resources
    await app.state.http_client.aclose()
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.project_name,
        version=settings.version,
        lifespan=lifespan,
    )

    # Register Routers
    app.include_router(auth_v1.router, prefix="/api/v1/auth", tags=["Auth V1"])
    app.include_router(users_v1.router, prefix="/api/v1/users", tags=["Users V1"])
    app.include_router(tasks_v1.router, prefix="/api/v1/tasks", tags=["Tasks V1"])

    return app


app = create_app()
```

---

## 5. Router Design

Routers are thin coordination layers:
1. Receive and deserialize HTTP requests.
2. Validate inputs automatically via Pydantic.
3. Resolve dependencies (auth, current user, db session, services).
4. Delegate work to the service layer.
5. Return typed response models with appropriate HTTP status codes.

```python
from fastapi import APIRouter, Depends, status
from app.api.deps import get_current_user, get_task_service
from app.models.user import User
from app.schemas.v1.task import TaskCreate, TaskResponse
from app.services.task import TaskService

router = APIRouter()


@router.post(
    "/",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
)
async def create_task(
    payload: TaskCreate,
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    return await service.create_task(user_id=current_user.id, data=payload)
```

---

## 6. Pydantic v2 Schemas

Strictly separate schemas by intent:
- **`Create`**: Fields required to create a resource.
- **`Update`**: Fields that can be partially updated (`None` default with optional types).
- **`Response`**: Fields exposed to clients (never leak password hashes or internal IDs).

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    is_completed: bool | None = None


class TaskResponse(TaskBase):
    id: int
    user_id: int
    is_completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

---

## 7. SQLAlchemy 2.x & Database Layer

### Declarative Models
```python
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    is_completed: Mapped[bool] = mapped_column(default=False, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="tasks")
```

### Async Database Session Management
Create engine and session factory once:

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
```

---

## 8. Repositories & Services

### Repository Pattern (Data Access)
```python
from collections.abc import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.task import Task
from app.schemas.v1.task import TaskCreate


class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, task_id: int) -> Task | None:
        stmt = select(Task).where(Task.id == task_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: int, offset: int = 0, limit: int = 20) -> Sequence[Task]:
        stmt = select(Task).where(Task.user_id == user_id).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, user_id: int, data: TaskCreate) -> Task:
        task = Task(user_id=user_id, **data.model_dump())
        self.session.add(task)
        await self.session.flush()
        await self.session.refresh(task)
        return task
```

### Service Pattern (Business Logic)
```python
from app.core.exceptions import TaskNotFoundError
from app.models.task import Task
from app.repositories.task import TaskRepository
from app.schemas.v1.task import TaskCreate


class TaskService:
    def __init__(self, repository: TaskRepository):
        self.repository = repository

    async def get_task(self, task_id: int, user_id: int) -> Task:
        task = await self.repository.get_by_id(task_id)
        if task is None or task.user_id != user_id:
            raise TaskNotFoundError(task_id)
        return task

    async def create_task(self, user_id: int, data: TaskCreate) -> Task:
        async with self.repository.session.begin():
            return await self.repository.create(user_id, data)
```

---

## 9. Dependency Injection (Wiring)

Use FastAPI dependencies to compose and inject repositories and services:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.repositories.task import TaskRepository
from app.services.task import TaskService


def get_task_repository(session: AsyncSession = Depends(get_db)) -> TaskRepository:
    return TaskRepository(session)


def get_task_service(
    repository: TaskRepository = Depends(get_task_repository),
) -> TaskService:
    return TaskService(repository)
```

---

## 10. Async I/O Guidelines

- Use `async def` for I/O-bound route handlers and database/HTTP operations.
- Never use blocking calls like `time.sleep()`, synchronous `requests.get()`, or blocking file operations in `async def`.
- For CPU-bound operations or synchronous libraries that cannot be made async, run them in threadpools:
  ```python
  from fastapi.concurrency import run_in_threadpool

  result = await run_in_threadpool(blocking_sync_function, arg1, arg2)
  ```

---

## 11. Pagination, Background Tasks, & Middleware

### Pagination
```python
from fastapi import Query


class PaginationParams:
    def __init__(
        self,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
    ):
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size
```

### Background Tasks vs. Queues
- **FastAPI `BackgroundTasks`**: Use ONLY for lightweight, fire-and-forget in-process tasks (e.g. audit log writing, simple metric increment).
- **Task Queues (Celery, ARQ, SAQ)**: Use for long-running jobs, email/SMS delivery, heavy data processing, and tasks requiring retry semantics and crash resilience.

---

## 12. Feature Development Workflow

When implementing any new feature in a FastAPI application, follow this sequence:

```text
Requirement Analysis
       ↓
API Contract & Schema Design (Pydantic v2)
       ↓
Database Model Updates & Alembic Migration
       ↓
Repository Layer Implementation (SQLAlchemy queries)
       ↓
Service Layer Implementation (Business rules & transactions)
       ↓
Router Endpoint & Dependency Wiring
       ↓
Validation & Unit/Integration Tests
```
