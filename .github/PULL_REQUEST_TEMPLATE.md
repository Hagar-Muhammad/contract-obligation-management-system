## Summary

<!-- What does this PR deliver, in a few sentences? -->

Closes #

## Requirements implemented

<!-- List every SRS ID this PR implements or changes. Keep docs/traceability.md in sync. -->

| Requirement | What was done | Test case(s) |
|---|---|---|
| FR-XXX-00 | | TC-XXX-00 |

## How it was tested

- [ ] Backend: `ruff check`, `ruff format --check`, `mypy`, `pytest` pass locally
- [ ] Frontend: `npm run lint`, `npm run format:check`, `npm run typecheck`, `npm test` pass locally
- [ ] Every requirement above has at least one test named by its TC ID
- [ ] Manual check (describe below)

<!-- Manual test steps, data used, edge cases checked. -->

## Screenshots (UI changes)

<!-- English and Arabic (RTL) screenshots for any new or changed screen. Delete this section if there is no UI change. -->

## Checklist

- [ ] Business rules and permissions are enforced in the backend, not only in the UI
- [ ] Database changes have an Alembic migration (upgrade and downgrade)
- [ ] `docs/traceability.md` updated
- [ ] Other docs updated if behaviour changed (`docs/*.md`)
- [ ] Decisions taken on the business's behalf are listed below and in `docs/decisions.md`

## Decisions made in this PR

<!-- Anything assumed that the business should confirm. "None" if nothing. -->
