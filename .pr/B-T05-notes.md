# B-T05 — Approval granular (v1b, tflyer-canvas)

Task dari fork `pram507/tflyer-canvas` backlog v1b. Repo SDK yang benar untuk
perubahan ini adalah `OpenHands/software-agent-sdk` (lihat AGENTS.md →
Cross-Repository Boundaries).

## Scope implementasi

Lapisan **additive & self-contained** di `openhands.sdk.security`:

1. `ConfirmTools` confirmation policy — tool-name gating:
   - `tools: list[str]` (tool yang wajib approve, unik & non-blank)
   - `should_confirm(risk, tool_name=None)` → True untuk tool terdaftar
   - `confirm_by_risk=True` → fallback ke risk threshold untuk tool lain
   - `tool_name` optional ditambahkan ke base + 3 policy existing (backward compatible)
2. `ToolApprovalSession` — session-scoped grant:
   - `grant(tool, scope="session")` only; `deny(tool, reason)`
   - TTL (default 300s) → `is_granted()` auto-deny + audit `TIMEOUT`
   - `audit_log()` → `ApprovalEntry(tool, decision, at, scope, reason)`

## Kriteria terima

| Kriteria | Status |
|----------|--------|
| tool terdaftar wajib approve | ✅ `ConfirmTools.should_confirm(tool_name=...)` |
| "approve all session" hanya sesi itu | ✅ `ToolApprovalSession` in-memory, tidak di-persist |
| timeout → deny otomatis | ✅ `is_granted()` expiry → `TIMEOUT` + False |
| semua tercatat | ✅ `audit_log()` GRANT/DENY/TIMEOUT |

## Verifikasi

| Perintah | Hasil |
|----------|-------|
| `uv run pytest tests/sdk/security/test_tool_approval.py` | 10 passed |
| `uv run pytest tests/sdk/security/test_confirmation_policy.py` | 17 passed (regresi) |
| `uv run pre-commit run --files <3 file>` | semua pass (ruff, pyright, import rules, secret fields) |

## Batasan (jujur)

- Perubahan ini **belum** di-wire ke `agent.py::_set_confirmation_status`
  maupun REST `/respond_to_confirmation` dan `clients/typescript`. Itu
  cross-layer change (contract + deprecation 5 minor + golden fixtures) dan
  perlu keputusan terpisah. Artefak ini menyediakan primitive yang bisa
  dipakai lapisan那些 without duplicating authorization logic.
- Tidak ada perubahan persisted settings / event schema → tidak ada schema
  version bump atau golden fixture yang diperlukan.
- Remote/fork control-plane (`pram507/tflyer-canvas`) perlu memanggil
  `ConfirmTools` + `ToolApprovalSession` saat mengkonfigurasi conversation;

  integrasi UI approval ada di repo Canvas (task terpisah).
