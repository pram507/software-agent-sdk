"""B-T05 — agent confirmation check honors tool names and session grants."""

from unittest.mock import MagicMock

from openhands.sdk import Agent
from openhands.sdk.security import (
    AlwaysConfirm,
    ConfirmTools,
    SecurityRisk,
)


def _state(policy, granted: bool):
    state = MagicMock()
    state.confirmation_policy = policy
    state.approval_session.is_granted.return_value = granted
    return state


def test_confirm_tools_gates_named_tool():
    """ConfirmTools requires confirmation for a listed tool even at low risk."""
    state = _state(ConfirmTools(tools=["execute_bash"]), granted=False)
    actions = [MagicMock(tool_name="execute_bash")]

    result = Agent._set_confirmation_status(state, [SecurityRisk.LOW], actions)

    assert result is True
    state.transition.assert_called_once()


def test_unlisted_tool_does_not_require_confirmation():
    state = _state(ConfirmTools(tools=["execute_bash"]), granted=False)
    actions = [MagicMock(tool_name="browser")]

    result = Agent._set_confirmation_status(state, [SecurityRisk.LOW], actions)

    assert result is False
    state.transition.assert_not_called()


def test_session_grant_skips_confirmation():
    """A previously granted tool runs without re-prompting this session."""
    state = _state(AlwaysConfirm(), granted=True)
    actions = [MagicMock(tool_name="execute_bash")]

    result = Agent._set_confirmation_status(state, [SecurityRisk.HIGH], actions)

    assert result is False
    state.transition.assert_not_called()
    state.approval_session.is_granted.assert_called_once_with("execute_bash")


def test_risks_and_actions_are_zipped():
    """A grant on one tool does not exempt a different pending tool."""
    state = MagicMock()
    state.confirmation_policy = ConfirmTools(
        tools=["execute_bash", "str_replace_editor"]
    )
    state.approval_session.is_granted.side_effect = [True, False]
    actions = [
        MagicMock(tool_name="execute_bash"),
        MagicMock(tool_name="str_replace_editor"),
    ]

    result = Agent._set_confirmation_status(
        state, [SecurityRisk.HIGH, SecurityRisk.HIGH], actions
    )

    assert result is True
    state.transition.assert_called_once()
