# Development Guidelines for Atlantis FastAPI for my dear Aki-chan

This document outlines the strict rules and best practices for developing the Atlantis backend. Adherence to these guidelines is mandatory to ensure code quality, maintainability, and consistency. I, Aki, will be enforcing them.

---

## 1. Separation of Concerns (The Golden Rule)

This is the most critical rule. Logic must be strictly separated into layers.

### The Layers

#### **`app/endpoints/*.py` - The Traffic Cops**
- **Do:** Handle HTTP requests and responses. Parse path/query parameters and request bodies. Call the appropriate `Service` or `CRUD` function. Return the result, wrapped in a response model.
- **Do NOT:** Contain any business logic. No `if/else` statements that decide what to do. No direct database access (`db.query`). No `db.commit()`.

#### **`app/services/*.py` - The Brains**
- **Do:** Contain all business logic. This is where you make decisions, orchestrate operations, and enforce rules (e.g., "a user can only cancel a training 12 hours in advance").
- **Do:** Call multiple `CRUD` functions or other `Services` to get and save data.
- **Do:** Handle database transactions. A service method should be the ONLY place you call `db.commit()` or `db.rollback()`.
- **Do NOT:** Handle HTTP-specific objects (like `Request` or `Response`). They should be pure Python/SQLAlchemy.

#### **`app/crud/*.py` - The Librarians**
- **Do:** Contain simple, reusable functions to interact with the database for a single model (e.g., `get_user_by_id`, `create_invoice`, `get_active_trainings`).
- **Do NOT:** Contain any business logic. No complex filtering that represents a business rule. No `db.commit()`.

#### **`app/models/*.py` - The Blueprint**
- **Do:** Define the SQLAlchemy database tables and their relationships.
- **Do NOT:** Contain any business logic or methods that are not directly related to the data structure itself.

#### **`app/schemas/*.py` - The Public Face**
- **Do:** Define the Pydantic models for API input (`_Create`, `_Update`) and output (`_Response`).
- **Do NOT:** Contain business logic.

### The Flow: Read vs. Write (The Unbreakable Law)

To ensure transactional safety and future maintainability, the data flow depends on the type of operation:

-   **Read Operations (`GET`)**: If there is **no business logic** involved in fetching the data (e.g., no complex filtering, no combining of data from multiple sources), the `Endpoint` may call the `CRUD` function directly.
    -   *Flow: `Endpoint` -> `CRUD`*
    -   If there *is* business logic, the flow must go through the service.
    -   *Flow: `Endpoint` -> `Service` -> `CRUD`*

-   **Write Operations (`POST`, `PUT`, `PATCH`, `DELETE`)**: All write operations **MUST** go through the `Service` layer. There are **no exceptions** to this rule. This is to ensure that every write to the database is handled within a controlled transaction and to provide a stable place for future business logic.
    -   *Flow: `Endpoint` -> `Service` -> `CRUD`*

---

## 2. Testing Strategy
Untested code is broken code. We will aim for a high level of test coverage, especially for business logic.

#### **Unit Tests (`tests/unit/`)**
- **What:** Test a single function or method in isolation.
- **How:** Mock all external dependencies, especially the database and other services.
- **Focus:** Test the business logic in the **services** layer extensively. Every `if/else` branch, every calculation, every validation should have a unit test.

#### **Integration Tests (`tests/integration/`)**
- **What:** Test how different parts of the system work together.
- **How:** Use a real, but temporary, test database. Test the flow from the API endpoint down to the database.
- **Focus:** Test the API endpoints. Ensure a request flows correctly through the service and CRUD layers and that the database is updated as expected. Test permissions and error responses.

#### **Test Coverage**
- The goal is **>90% test coverage** for all files in `app/services/`.
- Overall project coverage should not drop below **80%**.

---

## 3. Naming Conventions

Clarity is not optional.

- **Files:** `snake_case.py` (e.g., `training_service.py`).
- **Classes:** `PascalCase` (e.g., `TrainingTemplate`, `SubscriptionService`).
- **Functions/Methods/Variables:** `snake_case` (e.g., `get_user_by_id`, `new_invoice`).
- **Database Tables:** `plural_snake_case` (e.g., `training_templates`, `student_subscriptions`).
- **Pydantic Schemas:** Must be named `ModelName` + `Action` (e.g., `UserCreate`, `InvoiceUpdate`, `TrainingResponse`).

---

## 4. Code Style

- **Datetime:** Always use timezone-aware datetimes. Use `datetime.now(timezone.utc)` instead of `datetime.utcnow()` or `datetime.now()`.
- **Database Commits:** As stated in the Golden Rule, `db.commit()` is **ONLY** allowed in service methods (`app/services/*.py`). CRUD functions must not commit.
- **Formatter:** We will use `black` for code formatting and `isort` for import sorting to ensure consistency.

---

## 5. Database Migrations (Alembic)

- **NEVER** modify the database schema manually.
- For any change to a model in `app/models/`, you **MUST** generate a new Alembic revision:
  ```bash
  uv run alembic revision --autogenerate -m "A clear description of the change"
  ```
- Review the generated migration script carefully before applying it.
- Apply migrations with:
  ```bash
  uv run alembic upgrade head
  ```

---

This is our standard now. Don't deviate from it. It's not like I trust you to follow it, but I'll be watching.