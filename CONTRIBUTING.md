# Contributing

## Branches

| Branch | Purpose |
|---|---|
| `main` | Released, stable code. Changes arrive only through a release PR from `develop`. |
| `develop` | Integration branch. Every module PR targets `develop`. |
| `feature/<module>` | One module, e.g. `feature/contracts`. Branched from `develop`. |
| `fix/<short-name>` | Bug fix. Branched from `develop`. |
| `chore/<short-name>` / `docs/<short-name>` | Tooling, CI, documentation. |

Both `main` and `develop` are protected: changes go through a pull request, CI must pass, and force pushes
are blocked.

## Commits

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <summary in the imperative>

<optional body: why, and the requirement IDs involved>
```

- **Types:** `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`, `build`, `perf`.
- **Scopes:** the module (`auth`, `users`, `audit`, `parties`, `properties`, `contracts`, `documents`,
  `obligations`, `search`, `notifications`, `extraction`, `reports`) or an area (`backend`, `frontend`, `docs`, `ci`).
- Keep commits small and focused; a reviewer should understand each one on its own.

Example: `feat(contracts): reject end date earlier than start date (BR-03)`

## Pull requests

1. Open one issue per module (template: **Module**) listing its requirement IDs and acceptance criteria.
2. Branch from `develop`, implement backend + frontend + tests.
3. Open a PR into `develop` using the PR template. The description says `Closes #<issue>` and lists the
   requirement IDs implemented.
4. CI must be green. The reviewer merges with a **merge commit** so the individual Conventional Commits stay in
   history.

### Definition of done

- [ ] Every requirement in the PR has at least one automated test named by its test case ID.
- [ ] Business rules and permissions are enforced in the backend (the UI only mirrors them).
- [ ] Database changes come with an Alembic migration that upgrades and downgrades.
- [ ] New UI text exists in both `en.json` and `ar.json`, and the screen works in RTL.
- [ ] `docs/traceability.md` is updated; other docs are updated if behaviour changed.
- [ ] Any assumption made on the business's behalf is recorded in `docs/decisions.md` and in the PR.

## Tests and requirement IDs

- Test case `TC-CON-01` covers `FR-CON-01`, `TC-BR-03` covers `BR-03`, and so on.
- Backend: name the test `test_TC_CON_01_<what it checks>` and tag it:

  ```python
  @pytest.mark.req("FR-CON-01")
  def test_TC_CON_01_authorized_user_creates_contract(client): ...
  ```

- Frontend: put the ID in the `describe`/`it` name: `describe('TC-CON-01 create contract page', ...)`.
- Finding all tests for a requirement: search the repository for its TC ID.

## Code style

- **Backend:** ruff (lint + format), mypy in strict mode. Routers stay thin; business logic lives in services.
- **Frontend:** oxlint, Prettier, TypeScript strict. API types are generated from the backend's OpenAPI
  document; do not hand-write request/response types.
- Follow [docs/api-standards.md](docs/api-standards.md) for every endpoint.

## Running checks locally

See the "Running checks" table in [README.md](README.md). Run them before pushing; CI runs the same commands.
