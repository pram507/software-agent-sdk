"""B-T05 — granular tool approval: named tools, per-session grant, timeout, audit."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import BaseModel, ValidationError

from openhands.sdk.security.confirmation_policy import (
    AlwaysConfirm,
    ConfirmTools,
    NeverConfirm,
)
from openhands.sdk.security.risk import SecurityRisk
from openhands.sdk.security.tool_approval import (
    ApprovalDecision,
    ToolApprovalSession,
)


def _now() -> datetime:
    return datetime(2026, 11, 25, 12, 0, 0, tzinfo=UTC)


class TestConfirmToolsPolicy:
    def test_named_tool_always_requires_confirmation(self) -> None:
        policy = ConfirmTools(tools=["execute_bash", "str_replace_editor"])
        assert policy.should_confirm(tool_name="execute_bash") is True
        assert policy.should_confirm(tool_name="str_replace_editor") is True

    def test_unlisted_tool_does_not_require_confirmation(self) -> None:
        policy = ConfirmTools(tools=["execute_bash"])
        assert policy.should_confirm(tool_name="browser") is False
        assert policy.should_confirm(tool_name=None) is False

    def test_optional_risk_fallback(self) -> None:
        policy = ConfirmTools(tools=["execute_bash"], confirm_by_risk=True)
        assert (
            policy.should_confirm(tool_name="browser", risk=SecurityRisk.HIGH) is True
        )
        assert (
            policy.should_confirm(tool_name="browser", risk=SecurityRisk.LOW) is False
        )

    def test_blank_tool_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ConfirmTools(tools=["  "])

    def test_roundtrip_serialization(self) -> None:
        class Container(BaseModel):
            policy: ConfirmTools

        original = Container(policy=ConfirmTools(tools=["execute_bash"]))
        restored = Container.model_validate_json(original.model_dump_json())
        assert restored.policy.tools == ["execute_bash"]
        assert restored.policy.should_confirm(tool_name="execute_bash") is True

    def test_existing_policies_accept_tool_name_kwarg(self) -> None:
        assert AlwaysConfirm().should_confirm(tool_name="anything") is True
        assert NeverConfirm().should_confirm(tool_name="anything") is False


class TestToolApprovalSession:
    def test_grant_is_session_scoped(self) -> None:
        session = ToolApprovalSession(grant_ttl_sec=300)
        assert session.is_granted("execute_bash", now=_now()) is False

        session.grant("execute_bash", now=_now())
        assert session.is_granted("execute_bash", now=_now()) is True
        assert session.is_granted("other_tool", now=_now()) is False

    def test_grant_expires_and_is_denied(self) -> None:
        session = ToolApprovalSession(grant_ttl_sec=60)
        session.grant("execute_bash", now=_now())

        later = _now() + timedelta(seconds=61)
        assert session.is_granted("execute_bash", now=later) is False
        decisions = [entry.decision for entry in session.audit_log()]
        assert ApprovalDecision.TIMEOUT in decisions

    def test_explicit_deny_is_audited(self) -> None:
        session = ToolApprovalSession()
        session.deny("execute_bash", reason="user rejected", now=_now())
        entries = session.audit_log()
        assert entries[-1].decision is ApprovalDecision.DENY
        assert entries[-1].reason == "user rejected"
        assert session.is_granted("execute_bash", now=_now()) is False

    def test_audit_records_grant_with_scope(self) -> None:
        session = ToolApprovalSession()
        session.grant("execute_bash", scope="session", now=_now())
        entries = session.audit_log()
        assert entries[-1].decision is ApprovalDecision.GRANT
        assert entries[-1].scope == "session"
        assert entries[-1].tool_name == "execute_bash"
