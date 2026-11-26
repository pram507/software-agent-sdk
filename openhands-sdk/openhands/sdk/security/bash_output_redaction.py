"""Redact secret values from :class:`BashOutput` events (B-T06).

Uses :meth:`SecretRegistry.mask_secrets_in_model` so masking semantics stay in
one place: the same sentinel and the same "mask every resolved value, not only
exported" rule as stream/tool output. Base64 forms of already-tracked values
are masked too. Call this before persisting or publishing a ``BashOutput``.
"""

from pydantic import BaseModel

from openhands.sdk.conversation.secret_registry import SecretRegistry


def redact_bash_output[EventT: BaseModel](
    event: EventT, registry: SecretRegistry
) -> EventT:
    """Return a copy of ``event`` with registered secret values masked.

    The input is never mutated: the caller decides when to replace the event
    in the event store and on the outgoing stream, so both paths mask exactly
    the same content.
    """
    masked = registry.mask_secrets_in_model(event)
    data = masked.model_dump()
    updates = {}
    for field in ("stdout", "stderr"):
        text = data.get(field)
        if isinstance(text, str):
            redacted = registry.mask_encoded_secrets_in_output(text)
            if redacted != text:
                updates[field] = redacted
    return masked.model_copy(update=updates) if updates else masked
