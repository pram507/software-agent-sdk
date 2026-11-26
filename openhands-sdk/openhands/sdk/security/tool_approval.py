"""Session-scoped tool approval grants with expiry and audit trail (B-T05).

A grant authorizes a tool for the lifetime of one conversation session. It is
not persisted: restarting a conversation drops every grant. When a grant ages
out, :meth:`ToolApprovalSession.is_granted` records a timeout decision and
returns False, so the caller re-prompts the user (auto-deny on timeout).
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Literal


class ApprovalDecision(Enum):
    GRANT = "grant"
    DENY = "deny"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class ApprovalEntry:
    tool_name: str
    decision: ApprovalDecision
    at: datetime
    scope: Literal["once", "session"] = "session"
    reason: str = ""


class ToolApprovalSession:
    """In-memory approval state for a single conversation session."""

    def __init__(self, grant_ttl_sec: float = 300.0) -> None:
        self._ttl = timedelta(seconds=grant_ttl_sec)
        self._grants: dict[str, datetime] = {}
        self._audit: list[ApprovalEntry] = []

    def grant(
        self,
        tool_name: str,
        scope: Literal["once", "session"] = "session",
        now: datetime | None = None,
    ) -> None:
        moment = now or datetime.now(UTC)
        if scope == "session":
            self._grants[tool_name] = moment
        self._audit.append(
            ApprovalEntry(tool_name, ApprovalDecision.GRANT, moment, scope)
        )

    def deny(self, tool_name: str, reason: str, now: datetime | None = None) -> None:
        moment = now or datetime.now(UTC)
        self._grants.pop(tool_name, None)
        self._audit.append(
            ApprovalEntry(tool_name, ApprovalDecision.DENY, moment, "session", reason)
        )

    def is_granted(self, tool_name: str, now: datetime | None = None) -> bool:
        moment = now or datetime.now(UTC)
        granted_at = self._grants.get(tool_name)
        if granted_at is None:
            return False
        if moment - granted_at > self._ttl:
            self._grants.pop(tool_name, None)
            self._audit.append(
                ApprovalEntry(tool_name, ApprovalDecision.TIMEOUT, moment)
            )
            return False
        return True

    def audit_log(self) -> list[ApprovalEntry]:
        return list(self._audit)
