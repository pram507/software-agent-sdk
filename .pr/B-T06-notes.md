# B-T06 — Secret redaction di output BashOutput (v1b, tflyer-canvas)

Repo pemilik: `OpenHands/software-agent-sdk` (AGENTS.md → Cross-Repository
Boundaries). Fork kerja: `pram507/software-agent-sdk`.

## Implementasi

### Primitive

`openhands.sdk.security.bash_output_redaction.redact_bash_output`:
- Memakai `SecretRegistry.mask_secrets_in_model()` yang sudah ada — tidak ada
  parallel redaction / sentinel baru.
- Event input tidak dimutasi → hasil yang sama dipakai untuk event store dan
  outgoing stream.

### Integrasi penuh (commit ke-2)

| Layer | Perubahan |
|-------|-----------|
| `SecretRegistry` | `SECRET_MASK` jadi konstanta tunggal (3 literal disatukan) + `mask_encoded_secrets_in_output()` — masking bentuk base64 dari nilai yang sudah ter-export (tanpa I/O blocking) |
| `bash_output_redaction.py` | helper juga menutup bentuk base64 via `model_dump()`/`model_copy()` |
| `BashEventService` | field opsional `secret_registry`; `_redact_event()` + `_emit()` dipanggil di **semua** 3 titik emisi `BashOutput` (chunk, final, error) sebelum `_save_event_to_file` **dan** `_pub_sub` |

Ketika `secret_registry is None`, perilaku identik dengan sebelumnya (backward
compat). Deployment enterprise/control-plane yang memegang secret registry
menyuntiknya saat membuat `BashEventService`.

## Kriteria terima

| Kriteria | Status |
|----------|--------|
| `echo $SECRET` tidak menampilkan nilai | ✅ helper + wiring di emisi (saat registry disuntik) |
| grep event store atas nilai secret → 0 hit | ✅ `_save_event_to_file` meredaksi sebelum menulis |
| kebocoran base64 | ✅ ditutup di commit ke-2 |
| sentinel tunggal | ✅ `SecretRegistry.SECRET_MASK` |

## Verifikasi

| Perintah | Hasil |
|----------|-------|
| `uv run pytest tests/agent_server/test_bash_output_redaction.py` | 5 passed |
| `uv run pytest tests/agent_server/test_bash_service.py` | 25 passed |
| `uv run pytest tests/sdk/conversation/test_secrets_manager.py` | 30 passed |
| `uv run pytest tests/sdk/conversation tests/agent_server` | 4590 passed, 30 failed (lihat catatan) |
| `uv run pre-commit run --files <5 file>` | semua pass |

Catatan regression: 30 kegagalan pada suite gabungan semuanya di test OpenAPI
(`test_openapi_discriminator`, `test_runtime_router`, `test_search_limit_validation`,
`test_settings_router`) dan **lolos 125/125** saat dijalankan bersama dalam
grup terpisah — interference antar-test yang sudah ada, bukan efek perubahan
ini (perubahan hanya method/konstanta, bukan field Pydantic/schema).

## Batasan (jujur)

- `BashEventService` adalah singleton global tanpa akses ke `SecretRegistry`
  per-conversation. Hook redaction sudah terpasang, tetapi deployment harus
  menyuntik registry agar aktif; default `None` = tidak ada perubahan perilaku.
- Sisi Canvas tetap memakai pola `redact-mcp-secrets.ts` yang sudah ada untuk
  tampilan (task terpisah di repo Canvas).
