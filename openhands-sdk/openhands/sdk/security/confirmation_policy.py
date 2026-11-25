from abc import ABC, abstractmethod

from pydantic import Field, field_validator

from openhands.sdk.security.risk import SecurityRisk
from openhands.sdk.utils.models import DiscriminatedUnionMixin


class ConfirmationPolicyBase(DiscriminatedUnionMixin, ABC):
    @abstractmethod
    def should_confirm(
        self,
        risk: SecurityRisk = SecurityRisk.UNKNOWN,
        tool_name: str | None = None,  # noqa: ARG002
    ) -> bool:
        """Determine if an action with the given risk level requires confirmation.

        This method defines the core logic for determining whether user confirmation
        is required before executing an action based on its security risk level.

        Args:
            risk: The security risk level of the action to be evaluated.
                 Defaults to SecurityRisk.UNKNOWN if not specified.
            tool_name: Optional tool name for policies that gate specific tools.
                       Existing policies ignore this argument.

        Returns:
            True if the action requires user confirmation before execution,
            False if the action can proceed without confirmation.
        """


class AlwaysConfirm(ConfirmationPolicyBase):
    def should_confirm(
        self,
        risk: SecurityRisk = SecurityRisk.UNKNOWN,  # noqa: ARG002
        tool_name: str | None = None,  # noqa: ARG002
    ) -> bool:
        return True


class NeverConfirm(ConfirmationPolicyBase):
    def should_confirm(
        self,
        risk: SecurityRisk = SecurityRisk.UNKNOWN,  # noqa: ARG002
        tool_name: str | None = None,  # noqa: ARG002
    ) -> bool:
        return False


class ConfirmRisky(ConfirmationPolicyBase):
    threshold: SecurityRisk = SecurityRisk.HIGH
    confirm_unknown: bool = True

    @field_validator("threshold")
    def validate_threshold(cls, v: SecurityRisk) -> SecurityRisk:
        if v == SecurityRisk.UNKNOWN:
            raise ValueError("Threshold cannot be UNKNOWN")
        return v

    def should_confirm(
        self,
        risk: SecurityRisk = SecurityRisk.UNKNOWN,
        tool_name: str | None = None,  # noqa: ARG002
    ) -> bool:
        if risk == SecurityRisk.UNKNOWN:
            return self.confirm_unknown

        # This comparison is reflexive by default, so if the threshold is HIGH we will
        # still require confirmation for HIGH risk actions. And since the threshold is
        # guaranteed to never be UNKNOWN (by the validator), we're guaranteed to get a
        # boolean here.
        return risk.is_riskier(self.threshold)


class ConfirmTools(ConfirmationPolicyBase):
    """Require confirmation for an explicit list of tool names (B-T05).

    ``confirm_by_risk=True`` additionally defers to the risk threshold, so a
    listed tool always confirms while unlisted tools confirm only when risky.
    """

    tools: list[str] = Field(
        default_factory=list,
        description="Tool names that always require user confirmation.",
    )
    confirm_by_risk: bool = False
    risk_threshold: SecurityRisk = SecurityRisk.HIGH

    @field_validator("tools")
    @classmethod
    def validate_tools(cls, tools: list[str]) -> list[str]:
        cleaned = [name.strip() for name in tools if name.strip()]
        if len(cleaned) != len(tools):
            raise ValueError("tool names must not be blank")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("tool names must be unique")
        return cleaned

    def should_confirm(
        self,
        risk: SecurityRisk = SecurityRisk.UNKNOWN,
        tool_name: str | None = None,
    ) -> bool:
        if tool_name is not None and tool_name in self.tools:
            return True
        if self.confirm_by_risk:
            if risk == SecurityRisk.UNKNOWN:
                return True
            return risk.is_riskier(self.risk_threshold)
        return False
