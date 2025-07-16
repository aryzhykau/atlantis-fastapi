# Financial Service Refactoring TODO

- [x] **Create `app/services/financial.py`**: Establish the new file for the unified service.
- [x] **Consolidate Methods**: Move all relevant methods from `InvoiceService` and `PaymentService` into the new `FinancialService` class.
- [x] **Refactor Internal Calls**: Update any internal calls between the old services (e.g., `self.payment_service.some_method()`) to directly call the consolidated logic within `FinancialService`.
- [x] **Update CRUD Interactions**: Ensure all `invoice_crud` and `payment_crud` calls are correctly integrated within the new service.
- [x] **Adjust Dependencies**: Modify any `endpoints` or other `services` that currently import `InvoiceService` or `PaymentService` to import `FinancialService` instead.
- [x] **Remove Old Files**: Delete `app/services/invoice.py` and `app/services/payment.py`.
- [x] **Update `__init__.py`**: Adjust `app/services/__init__.py` to reflect the new service structure.
- [x] **Update Tests**: Create comprehensive tests for `FinancialService` that cover all existing functionality, aiming for >90% coverage as per `DEVELOPMENT_GUIDELINES.md`. Remove or refactor old tests for the individual services.
- [ ] **Run Quality Checks**: Execute `uv run ruff check .` and `uv run pytest` to ensure code quality and prevent regressions.
