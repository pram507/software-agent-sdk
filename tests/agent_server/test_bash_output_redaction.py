"""B-T06 — secret redaction at BashOutput emission/persistence."""

from datetime import UTC, datetime
from uuid import UUID

from openhands.agent_server.models import BashOutput
from openhands.sdk.conversation.secret_registry import SecretRegistry
from openhands.sdk.security.bash_output_redaction import redact_bash_output


def _event(stdout: str, stderr: str = "") -> BashOutput:
    return BashOutput(
        command_id=UUID("00000000-0000-0000-0000-000000000001"),
        order=0,
        stdout=stdout,
        stderr=stderr,
        timestamp=datetime(2026, 11, 25, 12, 0, 0, tzinfo=UTC),
    )


def _registry(token: str) -> SecretRegistry:
    registry = SecretRegistry()
    registry.track_exported_values({"API_TOKEN": token})
    return registry


def test_secret_value_is_redacted_in_stdout_and_stderr() -> None:
    registry = _registry("super-secret-token-123")
    event = _event("token=super-secret-token-123", "err super-secret-token-123")

    redacted = redact_bash_output(event, registry)

    assert redacted.stdout == "token=<secret-hidden>"
    assert redacted.stderr == "err <secret-hidden>"
    assert "super-secret-token-123" not in (redacted.stdout or "")
    assert "super-secret-token-123" not in (redacted.stderr or "")


def test_original_event_is_not_mutated() -> None:
    registry = _registry("abc123secret")
    event = _event("echo abc123secret")
    redact_bash_output(event, registry)
    assert event.stdout == "echo abc123secret"


def test_no_secrets_leaves_event_unchanged() -> None:
    registry = SecretRegistry()
    event = _event("plain output")
    redacted = redact_bash_output(event, registry)
    assert redacted.stdout == "plain output"


def test_base64_encoded_secret_is_not_covered() -> None:
    import base64

    token = "s3cr3t-value"
    registry = _registry(token)
    encoded = base64.b64encode(token.encode()).decode()
    event = _event(encoded)
    redact_bash_output(event, registry)
    assert encoded in (event.stdout or "")
