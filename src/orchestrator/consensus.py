"""Pure, deterministic consensus decisions."""

from __future__ import annotations

from fractions import Fraction
from typing import Literal

from .models import AgentVerdict

Decision = Literal["converge", "re_propose", "force_deliver"]


def decide(verdicts: list[AgentVerdict], round: int) -> Decision:
    """Choose the next step from validated verdicts and a bounded round number."""
    _validate_verdicts(verdicts)
    _validate_round(round)

    if not any(verdict.is_blocker for verdict in verdicts):
        return "converge"
    if round == 2:
        return "force_deliver"
    return "re_propose"


def confidence(verdicts: list[AgentVerdict]) -> int:
    """Calculate the specified 0--100 confidence without floating point arithmetic."""
    _validate_verdicts(verdicts)

    pass_count = sum(verdict.verdict == "PASS" for verdict in verdicts)
    hard_rules_passed = sum(verdict.hard_rules_passed for verdict in verdicts)
    hard_rules_total = sum(verdict.hard_rules_total for verdict in verdicts)
    no_blocker = not any(verdict.is_blocker for verdict in verdicts)

    score = Fraction(50 * pass_count, len(verdicts))
    score += 30 if no_blocker else 0
    score += Fraction(20 * hard_rules_passed, hard_rules_total)
    return _round_half_up(score)


def _validate_verdicts(verdicts: list[AgentVerdict]) -> None:
    if not isinstance(verdicts, list):
        raise TypeError("verdicts must be a list of AgentVerdict instances")
    if not verdicts:
        raise ValueError("verdicts must not be empty")
    if not all(isinstance(verdict, AgentVerdict) for verdict in verdicts):
        raise TypeError("verdicts must contain only AgentVerdict instances")


def _validate_round(round: int) -> None:
    if not isinstance(round, int) or isinstance(round, bool):
        raise TypeError("round must be an integer")
    if not 0 <= round <= 2:
        raise ValueError("round must be between 0 and 2")


def _round_half_up(value: Fraction) -> int:
    """Round a non-negative Fraction to nearest integer; .5 ties go upward."""
    return (2 * value.numerator + value.denominator) // (2 * value.denominator)
