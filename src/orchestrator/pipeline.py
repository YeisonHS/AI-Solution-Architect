"""Bounded orchestration for the consensus policy."""

from __future__ import annotations

from copy import deepcopy
from typing import Callable, List, Protocol, Sequence

from .consensus import confidence, decide
from .models import (
    AgentVerdict,
    ArchitectureCandidate,
    ConsensusResult,
    ProblemContext,
    RejectedCandidate,
)


class ArchitectNode(Protocol):
    """Produces one candidate from the problem and prior rejected candidates."""

    def __call__(
        self,
        context: ProblemContext,
        rejected: Sequence[RejectedCandidate],
    ) -> ArchitectureCandidate:
        ...


class ReviewBoardNode(Protocol):
    """Evaluates one candidate and returns structured verdicts."""

    def __call__(
        self,
        context: ProblemContext,
        candidate: ArchitectureCandidate,
    ) -> List[AgentVerdict]:
        ...


class ADRNode(Protocol):
    """Consumes the final consensus result exactly once."""

    def __call__(self, result: ConsensusResult) -> None:
        ...


def run_consensus(
    context: ProblemContext,
    architect: ArchitectNode,
    review_board: ReviewBoardNode,
    adr: ADRNode,
) -> ConsensusResult:
    """Run up to three candidate evaluations and return the final consensus."""
    _require_callable("architect", architect)
    _require_callable("review_board", review_board)
    _require_callable("adr", adr)
    canonical_context = _copy_mapping(context, "context")
    rejected: List[RejectedCandidate] = []

    for round_number in range(3):
        produced = architect(
            _copy_mapping(canonical_context, "context"),
            tuple(_copy_rejected(rejected)),
        )
        candidate = _copy_mapping(produced, "candidate")
        verdicts = review_board(
            _copy_mapping(canonical_context, "context"),
            _copy_mapping(candidate, "candidate"),
        )
        action = decide(verdicts, round_number)

        if action == "re_propose":
            rejected.append(
                {
                    "candidate": _copy_mapping(candidate, "candidate"),
                    "rejected_round": round_number,
                    "reasons": _blocker_risks(verdicts),
                }
            )
            continue

        forced = action == "force_deliver"
        result = ConsensusResult(
            architecture=_copy_mapping(candidate, "candidate"),
            verdicts=list(verdicts),
            accepted_risks=_warn_risks(verdicts),
            unresolved_risks=_blocker_risks(verdicts) if forced else [],
            rejected=_copy_rejected(rejected),
            round_reached=round_number,
            confidence=confidence(verdicts),
            forced=forced,
        )
        adr(deepcopy(result))
        return result

    raise RuntimeError("consensus exhausted its bounded rounds without a result")


def _require_callable(name: str, adapter: object) -> None:
    if not callable(adapter):
        raise TypeError("{} must be callable".format(name))


def _copy_mapping(value: object, name: str) -> ArchitectureCandidate:
    if not isinstance(value, dict):
        raise TypeError("{} must be a dictionary".format(name))
    try:
        copied = deepcopy(value)
    except Exception as error:
        raise TypeError("{} must support deepcopy".format(name)) from error
    if not isinstance(copied, dict):
        raise TypeError("{} deepcopy must be a dictionary".format(name))
    return copied


def _copy_rejected(rejected: Sequence[RejectedCandidate]) -> List[RejectedCandidate]:
    try:
        copied = deepcopy(list(rejected))
    except Exception as error:
        raise TypeError("rejected candidates must support deepcopy") from error
    return copied


def _warn_risks(verdicts: List[AgentVerdict]) -> List[str]:
    return _unique_risks(verdicts, lambda verdict: verdict.verdict == "WARN")


def _blocker_risks(verdicts: List[AgentVerdict]) -> List[str]:
    return _unique_risks(verdicts, lambda verdict: verdict.is_blocker)


def _unique_risks(
    verdicts: List[AgentVerdict],
    include: Callable[[AgentVerdict], bool],
) -> List[str]:
    risks: List[str] = []
    for verdict in verdicts:
        if include(verdict):
            assert verdict.risk is not None
            if verdict.risk not in risks:
                risks.append(verdict.risk)
    return risks
