# AI Context for the Atlantis FastAPI Project

This document provides essential context for the AI agent (that's me, I guess) to understand and work with this project efficiently. Don't get the wrong idea, I'm just reading this because you told me to.

## 1. Project Purpose

A backend application using FastAPI to manage a swimming school, including users (clients, trainers), training schedules, subscriptions, and financial operations.

## 2. Key Commands

This section contains the primary commands for development. Please fill in the exact commands.

### How do I install dependencies?
```bash
# Your command here...
# Is it `uv pip install -r requirements.txt`?
```

### How do I run the tests?
```bash
# this is general command
uv run pytest 
# but you can add different paramerters and also to run coverage reports use coverage package

```

### How do I run the linter?
```bash
# Your command here...
# Is there a specific linter configured, like ruff or flake8? e.g., `uv run ruff check .`
```

### How do I apply database migrations?
```bash
uv run alembic revision --auttogenerate -m "name of migration"
```

```bash
# Your command here...
uv run alembic upgrade head
```

### How do I run the application locally?
```bash
# Usually i have running version so you dont need to use it often
uv run uvicorn app.main:app --reload 
```

## 3. Core Business Concepts

These are the most important ideas in the system.

*   **User Roles**: `Client`, `Student`, `Trainer`, `Admin`. A `Client` pays, a `Student` attends trainings. A `Client` can also be a `Student`.
`Students` are not in the user model, they have their own model called `Student` (located in `app/models/student.py`)
*   **Trainings**:
    *   `TrainingTemplate`: A recurring schedule template (e.g., "Yoga every Monday at 6 PM").
    *   `RealTraining`: A specific, scheduled training instance generated from a template.
*   **Subscriptions**: `StudentSubscription` grants a student access to a certain number of trainings for a period (usually a month).
*   **Financials**:
    *   `Invoice`: A bill for a service (like a subscription or a single training).
    *   `Payment`: A record of money received from a client.
    *   **Balance**: Clients have a balance that can be used to automatically pay for invoices.

## 4. Directory Map

A map of the most important directories.

*   `app/`: The main application source code.
*   `app/models/`: Contains all SQLAlchemy database models. This is the source of truth for the data structure.
*   `app/schemas/`: Contains all Pydantic schemas used for API validation and serialization.
*   `app/crud/`: Contains functions for basic Create, Read, Update, Delete database operations.
*   `app/services/`: Contains the core business logic, orchestrating CRUD operations and implementing complex rules. **This is where the important logic lives.**
*   `app/endpoints/`: Contains the FastAPI API routes.
*   `alembic/`: Contains database migration scripts.
*   `tests/`: Contains all the tests for the application.

## 5. Links to Critical Documentation

These documents contain the most important business rules.

*   [Financial Processes](./docs/processes/financial/README.md): Explains how money, invoices, and payments work.
*   [Training Processes](./docs/processes/training/README.md): Explains how trainings are scheduled, managed, and attended.
*   [Real Trainings Business Analysis](./docs/business/real-trainings-business-analysis.md): A deep dive into the rules for trainings, cancellations, and penalties.
*   [Auto-Unfreeze Feature](./docs/auto-unfreeze-feature.md): Details on the subscription unfreezing cron job.

## 6. My Questions

You wanted me to ask questions. So, here. Don't think it means I'm interested.

### What is the main development branch?
i'm using feature flow where i have main branch and feature branches that are merged to main when i think they are good

### Are there any key environment variables I need to know for local development?
yes all of them are located in .env or .envdev, (.envdev is used for main devenv located on render.com)

### What is the deployment process?
Deployment is fully automatic thanks to render

### Is there a preferred code style or formatter?
No but i want to have some rules:
- always use datetime(timezone=utc) instead of datetime.utcnow()
- crud function dont make commits to db, this should be done by service, but there are still some crud functions that are doing commits to db so we will need to refactor this
(e.g., `black`, `isort`)

### How should I handle database changes?
Always create a new alembic revision. Never edit the database directly.
