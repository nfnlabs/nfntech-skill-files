---
name: fastapi-versioning
description: >-
  Architecture and lifecycle guide for API versioning in FastAPI applications.
  Covers URL versioning (/api/v1, /api/v2), version-specific routers and schemas,
  backward compatibility rules, deprecation lifecycles, and guidelines on when
  (and when not) to bump versions. Use when designing, evolving, or deprecating
  versioned APIs.
---

# FastAPI API Versioning & Architecture Skill

## 1. Role & Architectural Vision

You are an expert **FastAPI API architect** responsible for designing, versioning, evolving, and deprecating API endpoints cleanly while maintaining strict backward compatibility and seamless developer experience.

### Core Architectural Principle
```text
API versioning belongs at the API boundary.
Business logic and repositories should be shared whenever possible.
```

```text
                    Client
                      |
                      v
             ┌─────────────────┐
             │   FastAPI API   │
             └─────────────────┘
                      |
          ┌───────────┴───────────┐
          |                       |
       /api/v1                 /api/v2
          |                       |
          v                       v
    Versioned Router       Versioned Router
          |                       |
    Versioned Schema       Versioned Schema
          |                       |
          └───────────┬───────────┘
                      |
                      v
                Service Layer
                      |
                      v
              Repository Layer
                      |
                      v
                 PostgreSQL
```

---

## 2. Default Versioning Strategy

Always use **URL-based API versioning** as the default standard:

```text
/api/v1/users
/api/v1/tasks
/api/v1/auth/login

/api/v2/users
/api/v2/tasks
```

### Why URL Versioning?
* **Explicit & Visible**: Immediately apparent to API consumers and debuggers.
* **Simple Routing**: Directly maps to FastAPI router prefixes.
* **Clean Tooling**: Clean integration with Swagger UI / OpenAPI docs and testing clients.
* **Avoids Query/Header Ambiguity**: Query parameter versioning (`/users?v=2`) and custom Accept headers (`Accept: application/vnd.app.v1+json`) add routing friction and caching complications.

---

## 3. Project Structure for Versioned APIs

Organize routers and schemas by version while keeping services, repositories, and models shared:

```text
app/
├── main.py
├── api/
│   ├── deps.py
│   └── routes/
│       ├── v1/
│       │   ├── __init__.py
│       │   ├── users.py
│       │   └── tasks.py
│       └── v2/
│           ├── __init__.py
│           ├── users.py
│           └── tasks.py
├── models/                     # Shared database models
│   ├── user.py
│   └── task.py
├── schemas/                    # Version-specific DTOs
│   ├── v1/
│   │   ├── user.py
│   │   └── task.py
│   └── v2/
│       ├── user.py
│       └── task.py
├── repositories/               # Shared database queries
│   └── user.py
└── services/                   # Shared business logic
    └── user.py
```

### Application Factory Setup (`main.py`)
```python
from fastapi import FastAPI
from app.api.routes.v1 import users as users_v1
from app.api.routes.v2 import users as users_v2


def create_app() -> FastAPI:
    app = FastAPI(title="Production API", version="2.0.0")

    # Mount V1 Routers
    app.include_router(users_v1.router, prefix="/api/v1/users", tags=["Users V1"])

    # Mount V2 Routers
    app.include_router(users_v2.router, prefix="/api/v2/users", tags=["Users V2"])

    return app
```

---

## 4. Version-Specific Schemas

Each API version defines its own request/response schemas without altering the underlying database model:

### V1 Schema (`schemas/v1/user.py`)
```python
from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    id: int
    name: str
    email: str

    model_config = ConfigDict(from_attributes=True)
```

### V2 Schema with Restructured Profile (`schemas/v2/user.py`)
```python
from pydantic import BaseModel, ConfigDict


class UserProfile(BaseModel):
    name: str
    avatar_url: str | None = None


class UserResponse(BaseModel):
    user_id: int
    email: str
    profile: UserProfile

    model_config = ConfigDict(from_attributes=True)
```

---

## 5. Backward Compatibility & Breaking Changes

Treat every released API version as an **immutable contract**.

### Breaking Changes (Requires New API Version)
- Removing or renaming fields in request or response bodies.
- Changing field types (e.g. `user_id: int` → `user_id: str`).
- Changing required fields in requests.
- Restructuring response JSON hierarchy.
- Changing HTTP status codes for existing endpoints.
- Modifying authentication or permission requirements in a restrictive way.
- Removing an endpoint.

### Non-Breaking Changes (Keep Current API Version)
- Adding new optional fields to requests (with default values).
- Adding new fields to response bodies (if clients ignore unknown fields).
- Adding new endpoints to the existing version.
- Adding non-breaking optional query parameters.
- Performance improvements and internal refactorings.
- Bug fixes that restore intended contract behavior.

---

## 6. When (and When NOT) to Create a New Version

```text
Do NOT create a new API version for every release or feature addition.
Introduce a new major version (/api/v2) ONLY when breaking changes cannot be avoided.
```

---

## 7. API Version Lifecycle & Deprecation

Manage the lifecycle of API versions systematically:

```text
Development → Active (Current) → Deprecated → Sunset (Retired)
```

### Deprecating an Endpoint in FastAPI
Mark endpoints using the `deprecated=True` parameter on the router decorator:

```python
@router.get(
    "/users",
    response_model=list[UserResponseV1],
    deprecated=True,
    summary="List users (Deprecated: Use /api/v2/users)",
)
async def list_users_v1(service: UserService = Depends(get_user_service)):
    return await service.list_users()
```

### Deprecation Best Practices
1. **Announce**: Notify API consumers in advance with migration guides.
2. **Deprecation Headers**: Consider returning standard `Sunset` and `Deprecation` HTTP headers:
   ```text
   Deprecation: @1735689600
   Sunset: Wed, 01 Jul 2026 00:00:00 GMT
   Link: </api/v2/users>; rel="successor-version"
   ```
3. **Monitor Usage**: Track traffic to deprecated endpoints before full removal.
4. **Remove cleanly**: Only retire the version when client migrations are complete.

---

## 8. 10 API Versioning Golden Rules

```text
Rule 1: Use /api/v1/... as the default API versioning strategy.
Rule 2: Breaking changes require a new API version.
Rule 3: Do not duplicate business logic or repository queries between API versions.
Rule 4: Keep version-specific schemas in dedicated versioned modules (schemas/v1/, schemas/v2/).
Rule 5: Existing API versions must remain backward-compatible and stable.
Rule 6: Deprecate old API versions with advance notice and documentation before removal.
Rule 7: Test every supported API version with dedicated versioned test suites.
Rule 8: Document clear migration paths between API versions.
Rule 9: Do not bump versions for harmless backward-compatible additions.
Rule 10: Treat every public API version as an immutable contract.
```
