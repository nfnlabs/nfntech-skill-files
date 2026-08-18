---
name: fastapi-testing
description: >-
  Comprehensive testing guide for FastAPI applications using pytest, pytest-asyncio,
  and HTTPX AsyncClient. Covers unit and integration tests, database test fixtures
  with automatic transaction rollback, dependency overrides (app.dependency_overrides),
  version-specific test suites, external service mocking, and API contract validation.
  Use when writing, updating, or troubleshooting FastAPI test suites.
---

# FastAPI Testing Skill

## 1. Role & Principles

You are an expert **FastAPI test engineer** responsible for designing, implementing, and maintaining robust, isolated, and fast automated test suites for FastAPI applications.

### Core Testing Rules
- **Never connect tests to a production database.**
- **Isolate test side effects**: Every test must run in a clean state (using transaction rollback or isolated database fixtures).
- **Test the contract**: Verify status codes, header values, validation constraints, and response body schemas.
- **Do not mock everything**: Prefer testing real service + repository layers with an isolated test database. Mock only external third-party I/O (Stripe, SendGrid, external HTTP APIs).

---

## 2. Testing Stack & Setup

* **Framework**: `pytest`
* **Async Support**: `pytest-asyncio`
* **HTTP Client**: `httpx` (`AsyncClient`)
* **Mocking**: `unittest.mock` / `pytest-mock`

### `pytest.ini` / `pyproject.toml`
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
```

---

## 3. Core Fixtures & Async Client (`conftest.py`)

Set up reusable fixtures for the test database, async sessions, and `httpx.AsyncClient`:

```python
# tests/conftest.py
from collections.abc import AsyncGenerator
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app

settings = get_settings()

# Use dedicated test database URL
TEST_DATABASE_URL = settings.test_database_url or "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionFactory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Create tables once per test session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session per test with automatic rollback."""
    async with TestSessionFactory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTPX AsyncClient with dependency overrides wired to the test DB."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
```

---

## 4. Writing Route Tests

### 1. Happy Path & Status Codes
```python
# tests/v1/test_tasks.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_task_success(client: AsyncClient, auth_headers: dict):
    payload = {
        "title": "Build FastAPI Skill",
        "description": "Decompose into modular skills",
    }
    response = await client.post("/api/v1/tasks", json=payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]
    assert "id" in data
    assert data["is_completed"] is False
```

### 2. Validation Failures (422 Unprocessable Entity)
```python
@pytest.mark.asyncio
async def test_create_task_invalid_payload(client: AsyncClient, auth_headers: dict):
    # Missing required 'title'
    response = await client.post("/api/v1/tasks", json={}, headers=auth_headers)

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(err["loc"][-1] == "title" for err in errors)
```

### 3. Authentication & Authorization (401 / 403)
```python
@pytest.mark.asyncio
async def test_create_task_unauthenticated(client: AsyncClient):
    response = await client.post("/api/v1/tasks", json={"title": "Test"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_route_forbidden_for_regular_user(client: AsyncClient, regular_user_headers: dict):
    response = await client.delete("/api/v1/admin/users/1", headers=regular_user_headers)
    assert response.status_code == 403
```

### 4. Not Found (404) & Conflict (409)
```python
@pytest.mark.asyncio
async def test_get_nonexistent_task(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/tasks/99999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {"email": "existing@example.com", "password": "securepassword123"}
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
```

---

## 5. Dependency Overrides & Mocking

### Overriding Services or Authentication
```python
from app.api.deps import get_current_user
from app.models.user import User


@pytest.fixture
def override_current_user():
    fake_user = User(id=1, email="test@example.com", is_active=True, role="user")

    def _get_fake_user():
        return fake_user

    app.dependency_overrides[get_current_user] = _get_fake_user
    yield fake_user
    app.dependency_overrides.pop(get_current_user, None)
```

### Mocking External APIs
Use `pytest-mock` (`mocker`) or `unittest.mock.patch` to avoid hitting external networks:

```python
@pytest.mark.asyncio
async def test_payment_webhook(client: AsyncClient, mocker):
    mock_stripe = mocker.patch("app.services.payment.stripe.Charge.create")
    mock_stripe.return_value = {"id": "ch_123", "status": "succeeded"}

    response = await client.post("/api/v1/payments/charge", json={"amount": 5000})
    assert response.status_code == 200
    mock_stripe.assert_called_once()
```

---

## 6. Version-Specific Test Suite Structure

Organize tests strictly by API version to prevent regressions when evolving endpoints:

```text
tests/
├── conftest.py                 # Shared fixtures & test database setup
├── v1/
│   ├── test_auth.py
│   ├── test_users.py
│   └── test_tasks.py
└── v2/
    ├── test_users.py
    └── test_tasks.py
```

> **Regression Protection**: Modifying a v2 endpoint or schema must NEVER break existing test suites under `tests/v1/`.

---

## 7. API Contract Testing

Verify that response schemas adhere to API contracts over time:

```python
from app.schemas.v1.user import UserResponse as UserResponseV1
from app.schemas.v2.user import UserResponse as UserResponseV2


@pytest.mark.asyncio
async def test_v1_contract_stability(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/users/me", headers=auth_headers)
    assert response.status_code == 200
    # Validates response conforms precisely to V1 Pydantic model
    validated = UserResponseV1.model_validate(response.json())
    assert hasattr(validated, "name")


@pytest.mark.asyncio
async def test_v2_contract_conformance(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v2/users/me", headers=auth_headers)
    assert response.status_code == 200
    # Validates nested profile structure in V2
    validated = UserResponseV2.model_validate(response.json())
    assert hasattr(validated.profile, "name")
```
