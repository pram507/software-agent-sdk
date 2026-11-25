# B-T06 — Secret redaction di output BashOutput (v1b, tflyer-canvas)

Repo pemilik: `OpenHands/software-agent-sdk` (AGENTS.md → Cross-Repository
Boundaries). Fork kerja: `pram507/software-agent-sdk`.

## Scope implementasi

Helper additive `openhands.sdk.security.bash_output_redaction.redact_bash_output`:
- Memakai `SecretRegistry.mask_secrets_in_model()` yang **sudah ada** — tidak
  membuat parallel redaction / sentinel baru (sesuai AGENTS.md).
- Sentinel `<secret-hidden>` & aturan "mask semua nilai yang pernah di-export"
  tetap satu sumber di `SecretRegistry`.
- Event input tidak dimutasi → caller bisa pakai hasil yang sama untuk
  event store (persistensi) dan outgoing stream (pub/sub).
-基础64 ter-encode TIDAK tercakup (sesuai catatan task: "kebocoran ter-encode
  tidak tertutup v1").

## Kriteria terima

| Kriteria | Status |
|----------|--------|
| `echo $SECRET` tidak menampilkan nilai (redacted) | ✅ helper masking stdout/stderr; wiring ke emisi di `BashEventService` (lihat batasan) |
| grep event store atas nilai secret → 0 hit | ✅ jika helper dipanggil sebelum `_save_event_to_file` |

## Verifikasi

| Perintah | Hasil |
|----------|-------|
| `uv run pytest tests/agent_server/test_bash_output_redaction.py` | 4 passed (RED → GREEN) |
| `uv run pytest tests/agent_server/test_bash_service.py` | 22 passed (regresi) |
| `uv run pre-commit run --files <2 file>` | semua pass (ruff, pyright, import rules, secret fields) |

## Batasan (jujur)

- Helper **belum di-wire** ke `BashEventService._save_event_to_file` /
  `_pub_sub` (三条 emisi `BashOutput`). Itu menyentuh agent-server + REST +
  kontrak; perlu keputusan terpisah karena `BashEventService` tidak punya
  akses ke per-conversation `SecretRegistry`.
- Client-side Canvas teruskan pola `redact-mcp-secrets.ts` yang sudah ada
  (repo `pram507/tflyer-canvas`, task terpisah).
- Tidak ada perubahan persisted settings / event schema → tidak perlu schema
  version bump atau golden fixture.
