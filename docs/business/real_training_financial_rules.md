# Real Trainings — Financial & Cancellation Rules (Implementation Guide)

This document describes the current business logic implemented in the codebase for real trainings, student registrations, cancellations, invoices, payments and the daily processing flow. It maps rules to files and functions so engineers can reason about correctness, idempotency and where to change behaviour safely.

Summary / purpose
- Ensure trainings, cancellations, invoices and payments follow clear rules.
- Make operations transactional and idempotent where required.
- Avoid double deductions and accidental refunds for non-paid invoices.

Quick locations (core files)
- Models
  - `app/models/real_training.py` — `RealTraining`, `RealTrainingStudent` (field: `session_deducted`, `processed_at`, `requires_payment`).
  - `app/models/invoice.py` — `Invoice`, `InvoiceStatus`, `InvoiceType`, and `cancelled_by_id`.
- CRUD
  - `app/crud/real_training.py` — generation & DB helpers: `generate_next_week_trainings`, `add_student_to_training_db`, `get_real_training`, `get_real_training_student`.
  - `app/crud/invoice.py` — invoice CRUD helpers: `create_invoice`, `cancel_invoice`, `mark_invoice_as_unpaid`, `mark_invoice_as_paid`, `get_training_invoice`.
- Services
  - `app/services/financial.py` — `FinancialService`: invoice creation (`create_standalone_invoice`), auto-pay (`_attempt_auto_payment`), refunding (`_refund_paid_invoice`), registering payments.
  - `app/services/training_processing.py` — `TrainingProcessingService`: per-training and per-student processing for "tomorrow" trainings; contains the meat of when to deduct sessions, create/finalize invoices and attempt auto-pay.
  - `app/services/real_training.py` — `RealTrainingService`: endpoint-level operations for cancelling student/training, and helper flows that call `FinancialService` and `TrainingProcessingService`.
  - `app/services/daily_operations.py` — orchestrates daily operations and calls training processing for tomorrow.
- Endpoints
  - `app/endpoints/real_trainings.py` — endpoints invoking service layer for generation, cancellation, attendance updates and student cancels.

Business rules (current implementation)

1) Model additions & fields
- `RealTrainingStudent.session_deducted` (Boolean, default False): indicates whether a subscription session has already been deducted for this student+training. Prevents double-deduction.
- `RealTraining.processed_at` (DateTime, nullable): indicates that the training has been processed by the daily job (used to decide whether to return sessions on cancellation).
- `RealTrainingStudent.requires_payment` (Boolean): flag used to skip automatic invoice creation when a payment/penalty already handled manually.

Where implemented:
- `app/models/real_training.py` (fields)
- Alembic migration: `alembic/versions/20250915_add_session_deducted_to_real_training_students.py` (added `session_deducted` column).

2) Training generation (weekly cron / API)
- `generate_next_week_trainings` creates RealTraining rows from templates and copies eligible template students into RealTrainingStudent rows with status REGISTERED.
- When copying template students, logic checks `training_type.is_subscription_only`. If subscription-only, the student is added only if they have an active StudentSubscription valid for that training date with sessions left or auto-renew enabled.
- During generation, `RealTrainingStudent.requires_payment` defaults to True — the daily processing layer decides invoice creation later.

Where implemented: `app/crud/real_training.py::generate_next_week_trainings`

3) Invoice creation and pay-per-session vs subscription users (daily processing)
- The daily processing runs over trainings scheduled for TOMORROW with `processed_at IS NULL`. Each training is processed in its own transaction (TrainingProcessingService.process_tomorrow_trainings).
- For each student:
  - If an active subscription is present for the training date: do NOT create an invoice. Instead, if `session_deducted` is False -> deduct 1 session (decrement `StudentSubscription.sessions_left`) and set `session_deducted = True`.
    - If `session_deducted` is already True, skip deduction (idempotency guard).
  - If no active subscription: pay-per-session flow applies.
    - If there is no invoice for that training/student: create an UNPAID invoice (NOT PENDING) and, as part of the same transaction, attempt auto-payment immediately (FinancialService.create_standalone_invoice with auto_pay True for UNPAID). Note: the code path creates UNPAID invoice when student present and attempts payment.
    - If a PENDING invoice already exists (e.g., created earlier due to a late-cancellation penalty or earlier step), the processing will move it to UNPAID and then attempt auto-payment immediately.

Where implemented:
- `app/services/training_processing.py::_process_student_training`
- `app/services/financial.py::_create_and_process_invoice_logic` and `_attempt_auto_payment`

4) Cancellation handling — per-student
- There are two high-level cancellation types: SAFE (timely) and PENALTY (late/no-show). Cancellation decision is based on `_check_cancellation_time` which uses training type rules (safe hours/times) or a fallback SAFE_CANCELLATION_HOURS.

SAFE_CANCEL (CANCELLED_SAFE)
- Subscription users:
  - If `session_deducted == True` (the training was processed and a session was deducted) -> return the session: increment `StudentSubscription.sessions_left` and set `session_deducted = False`.
  - If `session_deducted == False` -> do nothing for subscription sessions (nothing to return).
- Pay-per-session users (invoice exists for that training):
  - If invoice.status == PAID -> perform refund (increase client balance and cancel invoice) via FinancialService._refund_paid_invoice.
  - If invoice.status in (UNPAID, PENDING) -> cancel invoice (mark CANCELLED) with NO financial operation.
- Important: refunds are performed only for actually PAID invoices.
- Invoice cancellation (UNPAID/PENDING) will not touch client balance.

LATE_CANCEL / NO_SHOW (CANCELLED_PENALTY / ABSENT)
- Subscription users:
  - If `session_deducted == False` -> deduct a session (decrement `sessions_left`) and set `session_deducted = True`.
  - If `session_deducted == True` -> skip (already deducted earlier).
- Pay-per-session users:
  - If there is already a PENDING invoice: mark it UNPAID and attempt auto-payment immediately.
  - If there is already an UNPAID invoice: attempt auto-payment immediately.
  - If no invoice exists: create a PENDING invoice, then (in the same student-level flow) move it to UNPAID and attempt auto-payment immediately.

Where implemented:
- Cancellation endpoints call into `RealTrainingService._cancel_student_logic` (app/services/real_training.py) that decides SAFE vs PENALTY and calls `_process_safe_cancellation_refunds` or `_apply_cancellation_penalty`.
- The per-student logic for finalizing PENDING->UNPAID and auto-pay lives in `TrainingProcessingService._process_student_training`.

5) Full-training cancellation
- Cancelling a whole training marks `RealTraining.cancelled_at` and `cancellation_reason` and iterates all students calling `_process_training_cancellation_refunds` which mirrors per-student SAFE logic:
  - Return subscription session if `session_deducted == True`.
  - If invoice found: if PAID -> refund; else cancel invoice without financial operation.

Where implemented: `RealTrainingService._cancel_training_logic` and `_process_training_cancellation_refunds`.

6) Invoice lifecycle rules (as implemented)
- Invoice statuses: PENDING, UNPAID, PAID, CANCELLED.
- PENDING invoice is considered a placeholder and is NOT auto-paid when created.
- Only UNPAID invoices are eligible for auto-payment attempts (_attempt_auto_payment).
- When a PENDING invoice must be finalized (e.g., training presence or penalty), it is moved to UNPAID and then the system immediately attempts auto-payment.
- Refunds: only attempted on PAID invoices. The refund code increments client balance and marks the invoice CANCELLED.

Where implemented: `app/crud/invoice.py` (status transitions) and `app/services/financial.py` (`_attempt_auto_payment`, `_refund_paid_invoice`).

7) Client payments (manual payments registered)
- `FinancialService.register_standalone_payment` creates a Payment record and then applies it to UNPAID invoices only (calls `invoice_crud.get_unpaid_invoices` and pays invoices in order).
- Important: PENDING invoices are not targeted by client payments until they are finalized to UNPAID.

Where implemented: `app/services/financial.py::_register_payment_logic`.

8) Transactions and atomicity
- TrainingProcessingService processes each training in its own transaction (the outer loop calls `transactional(self.db)` per training). Within that, each per-student operation modifies subscription sessions, invoice status and attempts auto-pay — these modifications happen inside the same DB transaction, so failures cause rollback for that training.
- `FinancialService.create_standalone_invoice` wraps creation/initial processing in a transaction.
- RealTrainingService endpoints typically call service functions inside `transactional(self.db)` in `RealTrainingService.cancel_student` and `cancel_training`.

Where implemented: `app/database.py` (transactional helper used across services), and usage in `TrainingProcessingService`, `FinancialService`, `RealTrainingService`.

9) Logging and idempotency
- Functions log important steps: session deductions/returns, invoice creation, invoice finalization attempts, skipped students, and exceptions.
- Idempotency guards:
  - `session_deducted` prevents double deduction/return of subscription sessions.
  - `RealTraining.processed_at` marks trainings as already processed so daily job is repeatable.
  - Invoice lookup filters out CANCELLED invoices to avoid re-processing cancelled entries.

10) Integrity rules enforced by code
- Subscription sessions are only deducted when `session_deducted` is False; returned only when it was True.
- PENDING invoices are not auto-paid at creation; they are only finalized to UNPAID when business rules dictate.
- Refunds are only attempted for invoices whose status is PAID.
- Financial operations (balance updates, invoice status changes) happen inside transactions and use central `FinancialService` flows.

Implementation notes and specific code references (high-value anchors)
- Deduction guard and per-student processing:
  - `app/services/training_processing.py::_process_student_training` — lines around handling `active_subscription` and `session_deducted`.
- Creating invoices and not auto-paying PENDING:
  - `app/services/financial.py::_create_and_process_invoice_logic` — logs when PENDING created and exits without auto-pay.
- Auto-payment (UNPAID only):
  - `app/services/financial.py::_attempt_auto_payment` — checks balance and marks invoice PAID and updates user balance.
- Refund only for PAID:
  - `app/services/financial.py::_refund_paid_invoice` — checks status==PAID before refunding and cancelling invoice.
- Cancellation flows:
  - `app/services/real_training.py::_process_safe_cancellation_refunds` (SAFE cancel) and `_process_training_cancellation_refunds` (full-training cancel)
  - `app/services/real_training.py::_apply_cancellation_penalty` (LATE_CANCEL applies subscription deduction OR creates PENDING invoice)
- Daily entrypoint: `app/services/daily_operations.py::DailyOperationsService.process_daily_operations` calls training processing service.
- Cron endpoint: `app/endpoints/real_trainings.py::generate_next_week_endpoint` is API-protected by an API key for generation; daily processing is triggered by `FinancialService.process_invoices` pointing to `TrainingProcessingService.process_tomorrow_trainings`.

Edge cases & behaviour observed in code
- If `price <= 0` the code avoids creating invoices and marks the action as skip_free_training.
- When creating invoices for penalties the code creates PENDING first (auto_pay=False) and then immediately marks it UNPAID and attempts auto-payment — this is done to follow the rule "PENDING invoices are never auto-paid at creation" but are finalized immediately when required by penalty rules.
- When cancelling a training where processed_at is NULL (not processed) the code will not return subscription sessions (since they weren't deducted yet).
- Training/student cancellation functions set `cancelled_at` timestamp (ensuring auditability).

Assumptions in current code (implicit)
- `transactional(self.db)` is a context manager that begins/commits/rolls-back transactions; it is used per training and per create invoice flow.
- `Student.client.balance` is used as the authoritative client balance for auto-pay/refund logic; it may be None and code treats that as 0.
- `cancelled_by_id` is expected on Invoice but training/student objects may not have cancelled_by_id — code uses fallbacks (some places expect an id, some pass 0 or 1).

Suggested clarifications / improvements (low-risk, prioritized)
1. Centralize cancelled_by handling: pass `processed_by_id` from endpoints uniformly into cancellation/refund flows so audit trail is consistent (currently some code uses default 0 or 1).
2. Explicitly separate "create PENDING invoice" and "finalize to UNPAID + auto-pay" into distinct helper functions in FinancialService to make it easier to reason about idempotency and logging.
3. Add tests for the exact invariant: PENDING invoices are never auto-paid at creation (and UNPAID triggers auto-pay attempts).
4. Improve Transactional scopes: ensure per-student operations are individually transactional when called from endpoints; TrainingProcessingService already treats per-training transaction.
5. Add clearer logs when refunds are skipped because invoice was not PAID.

Where to read the code (quick links)
- Per-student processing & invoices: `app/services/training_processing.py`
- Cancellation flows: `app/services/real_training.py`
- Invoice/payment primitives: `app/services/financial.py` and `app/crud/invoice.py`
- Models: `app/models/real_training.py`, `app/models/invoice.py`

Usage examples (behavioral examples)
- Generation (Monday): admin or cron calls `POST /real-trainings/generate-next-week` which runs `generate_next_week_trainings` and creates training rows with registered students from templates.
- Next-day daily cron: system calls financial/process_invoices or scheduling service calls DailyOperationsService.process_daily_operations -> TrainingProcessingService.process_tomorrow_trainings which:
  - Deducts subscription sessions (once) for students with subscriptions.
  - Creates/finalizes invoices for pay-per-session students, attempts auto-pay when invoice moves to UNPAID.
  - Marks each training `processed_at` after completion.
- Real-time cancellations: endpoints call `RealTrainingService.cancel_student` or `cancel_training` which:
  - If SAFE: return sessions if previously deducted, cancel or refund invoice only if PAID.
  - If LATE/NO_SHOW: deduct sessions (subscription) or create/finalize invoices and attempt auto-pay immediately.

Quality gates & test coverage notes
- Critical behaviors to assert in tests:
  1. Subscription session never deducted twice (session_deducted guard).
  2. PENDING invoice is not auto-paid at creation.
  3. When PENDING -> UNPAID the system attempts auto-pay immediately.
  4. Refund happens only for PAID invoices, not for UNPAID/PENDING.
  5. Training `processed_at` guards re-processing.

If you want, next steps I can take now
- Produce a compact sequence diagram for core flows (generate -> process -> cancel) to paste into this doc.
- Add a couple of unit tests that assert the invariants (idempotent deductions, pending->unpaid auto-pay behavior).
- Normalize `cancelled_by` propagation by changing endpoints to pass the current user id into refund/cancel calls.


Document created by automated code analysis on: 2025-09-15

