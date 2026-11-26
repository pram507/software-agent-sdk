# B-T05 — Approval granular (v1b, tflyer-canvas)

Task dari fork `pram507/tflyer-canvas` backlog v1b. Repo pemilik:
`OpenHands/software-agent-sdk` (AGENTS.md → Cross-Repository Boundaries).

## Implementasi

### Primitive (`openhands.sdk.security`)

1. `ConfirmTools` — tool-name gating:
   - `tools: list[str]` (tool yang wajib approve, unik & non-blank)
   - `should_confirm(risk, tool_name=None)` → True untuk tool terdaftar
   - `confirm_by_risk=True` → fallback ke risk threshold untuk tool lain
   - `tool_name` optional ditambahkan ke base + 3 policy existing (backward compat)
2. `ToolApprovalSession` — session-scoped grant:
   - `grant(tool, scope="session")`; `deny(tool, reason)`
   - TTL (default 300s) → `is_granted()` auto-deny + audit `TIMEOUT`
   - `audit_log()` → `ApprovalEntry(tool, decision, at, scope, reason)`

### Integrasi penuh (commit ke-2)

| Layer | Perubahan |
|-------|-----------|
| `ConversationState` | `_approval_session` **PrivateAttr** (never serialized) + `approval_session` property — grant hanya hidup di sesi in-memory |
| `Agent._set_confirmation_status` | zip `risks` × `action_events`, lewati tool yang sudah di-grant, teruskan `tool_name` ke `should_confirm` |
| `ConfirmationResponseRequest` (REST) | field `scope: Literal["once","session"] = "once"` (backward compat) |
| `EventService.respond_to_confirmation` | `scope="session"` → `_grant_pending_tools_for_session()` sebelum `run()`; grant `tool_name` dari `get_unmatched_actions(active_branch())` |
| `security/__init__.py` | ekspor `ConfirmTools`, `ToolApprovalSession`, `ApprovalDecision`, `ApprovalEntry` |
| Typed client | `ConfirmationScope` + `scope?` di `ConfirmationResponseRequest`, `sendConfirmationResponse(accept, reason?, scope?)` di base/remote/local client, generated schema, public index |

## Kriteria terima

| Kriteria | Status |
|----------|--------|
| tool terdaftar wajib approve | ✅ `ConfirmTools` + `Agent._set_confirmation_status` |
| "approve all session" hanya sesi itu | ✅ grant di `ConversationState` PrivateAttr, hilang saat restart |
| timeout → deny otomatis | ✅ `is_granted()` expiry → `TIMEOUT` + False |
| semua tercatat | ✅ `audit_log()` GRANT/DENY/TIMEOUT |
| REST menerima scope | ✅ `ConfirmationResponseRequest.scope` |
| typed client mengirim scope | ✅ test `api-clients.test.ts` |

## Verifikasi

| Perintah | Hasil |
|----------|-------|
| `uv run pytest tests/sdk/security/test_tool_approval.py` | 10 passed |
| `uv run pytest tests/agent/test_granular_confirmation.py` | 4 passed |
| `uv run pytest tests/agent_server/test_event_service.py` | 161 passed |
| `uv run pytest tests/sdk/conversation tests/agent tests/agent_server/test_event_service.py` | 1253 passed |
| `uv run pre-commit run --files <semua file>` | semua pass (ruff, pyright, import rules, secret fields) |
| `clients/typescript`: `npm run build` | pass |
| `clients/typescript`: `npm test` | 452 passed |
| `clients/typescript`: `npm run lint` | 0 error (5 warning existing) |
| `clients/typescript`: `npm run check:public-type-budget` | unchanged (103 sites) |

## Batasan (jujur)

- `check:agent-server-api` tidak dijalankan: generator mengambil OpenAPI dari
  **rilis SDK terpin**, belum mengandung field `scope`. File generated di-update
  manual sebagai jembatan pengembangan; akan tergenerate ulang otomatis saat
  rilis SDK berikutnya memuat kontrak ini.
- Tidak ada perubahan persisted settings / event schema → tidak perlu schema
  version bump atau golden fixture.
- UI approval di Canvas (`pram507/tflyer-canvas`) masih perlu memanggil
  `sendConfirmationResponse(..., scope="session")` — task terpisah di repo Canvas.
