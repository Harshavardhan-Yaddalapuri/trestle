# Code Review: `review/jules-prep-orchestrator-merge`

## Per-File Findings

| File | Assessment | Details & Suggested Fix |
|---|---|---|
| `backend/api/auth.py` | OK | Reduced to just `GET /me` with lazy provisioning. This is correct as Supabase handles the actual authentication flows. |
| `backend/api/grants.py` | OK | Resolved successfully. The extraction of lifecycle logic is clean, and the `owner_clause` works well. |
| `backend/api/lifecycle.py` | OK | Extracted cleanly from `grants.py` with standard Supabase/Session-based tracking. |
| `backend/api/health.py` | OK | Adapted to check Supabase JWKS connectivity. Matches orchestrator standard. |
| `backend/api/memory.py` | OK | Applies `owner_clause` appropriately. |
| `backend/api/users.py` | BUG | `from backend.core.errors import AuthenticationError` is inside `_require_user` function. Move to top-level imports. |
| `backend/api/__init__.py` | OK | Registers the new `lifecycle` and `email` routers successfully. |
| `backend/db/models/user.py` | OK | Minimal user model matched for Supabase needs. Good use of JSONB for alerts. |
| `backend/db/models/grant_association.py` | OK | Clean extensions for lifecycle statuses and events. |
| `backend/db/models/__init__.py` | OK | Exported `GrantLifecycleEvent` and dropped `UserSession`. |
| `backend/services/scheduler.py` | OK | Schedulers successfully resolved with the orchestrator patterns. |
| `backend/tests/conftest.py` | DEAD CODE | Contains `mock_successful_jwt_verification` and patches to `backend.api.auth.create_client` which are no longer needed. Remove the obsolete mock fixtures. |
| `backend/middleware/auth.py` | OK | Parses Supabase JWT correctly, establishing `UserCtx`. Follows standard best practices for auth middlewares. |
| `backend/migrations/versions/0015_users_alert_prefs.py` | SCHEMA | Missing foreign keys for related tables linking to this `users` table since `UserSession` is gone. Though, maybe that is not necessary if relying on `session_id`/`sub`. It accurately creates the table matching the model. |

## Judgment Call Validation

1. **Killed magic-link auth entirely.**
   **KEEP:** With Supabase as the primary auth mechanism, maintaining a custom magic link implementation is redundant and increases security risks.
2. **Added a new `users` table for alert_preferences.**
   **KEEP:** It allows mapping Supabase identities (`sub`) to custom app settings without cluttering auth context.
3. **Extracted lifecycle into `api/lifecycle.py`.**
   **KEEP:** Prevents `api/grants.py` from becoming bloated.
4. **Rewrote alert-preferences endpoints.**
   **KEEP:** Better to rely on the minimal User schema now rather than `UserSession`.
5. **Left `backend/services/auth/*` as dead code.**
   **REVERSE:** If magic-link auth is killed, `backend/services/auth/` (like `identity.py`, `merge.py`, `tokens.py`) shouldn't exist unless strictly required for something else. `merge.py` still operates on `from_session_id`, which might be required for anon->auth transitions but should be reviewed or pruned.
6. **Moved 3 magic-link test files to `.trestle-disabled/`.**
   **REVERSE:** They were DELETED, not moved. The diff shows `D backend/tests/test_auth_private.py` and `D backend/tests/test_auth_public.py`. The CoS failed to move them to `.trestle-disabled/` as claimed. They should either be properly archived or simply deleted forever since auth is now on Supabase.
7. **Lazy provisioning in `auth.py`.**
   **KEEP:** Standard practice for synchronizing external identity providers (like Supabase) into the local database schema seamlessly.

## Critical Issues (Block Merge)
* **Missing Disabled Tests:** The CoS stated it moved 3 test files to `.trestle-disabled/`, but the git diff shows they were permanently deleted (`test_auth_private.py`, `test_auth_public.py`). If the intention was to keep them for reference, they need to be restored and placed in that directory.

## Important Issues (Should Fix Before Merge)
* **Dead Code - `backend/services/auth/`:** Review if `merge.py` and other files are strictly necessary. If `UserSession` is removed, the identity merging logic may be obsolete or need heavy modification. Remove if fully obsolete.
* **Dead Code - `conftest.py`:** Delete the no-op Supabase patches that references `backend.api.auth.create_client` and other non-existent paths.
* **Bug in `users.py`:** Move `AuthenticationError` import to the top of the file.

## Nice-to-Have
* Address minor flake8 linting warnings (e.g., lines too long).

## Recommended Next Steps
1. Restore deleted test files into `.trestle-disabled/` if they are intended to be kept.
2. Clean up `backend/services/auth/` dead code.
3. Clean up `conftest.py` mock remnants.
4. Refactor `users.py` import logic.
5. Review the `merge.py` logic if anon sessions are still a thing and properly migrate them to the new schema constraints.
