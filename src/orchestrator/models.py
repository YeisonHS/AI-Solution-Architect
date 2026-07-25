"""Structured domain models for the deterministic consensus policy."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, TypedDict

ArchitectureCandidate = Dict[str, Any]
ProblemContext = Dict[str, Any]

_AGENT_PATTERN = re.compile(r"[a-z][a-z0-9_-]*\Z")
_VALID_VERDICTS = {"PASS", "WARN", "FAIL"}


@dataclass(frozen=True)
class AgentVerdict:
    """A validated, machine-readable assessment from one board agent."""

    agent: str
    verdict: str
    severity: str
    risk: Optional[str]
    hard_rules_passed: int
    hard_rules_total: int

    def __post_init__(self) -> None:
        if not isinstance(self.agent, str) or not _AGENT_PATTERN.fullmatch(self.agent):
            raise ValueError("agent must be a non-empty, lowercase canonical identifier")
        if self.verdict not in _VALID_VERDICTS:
            raise ValueError("verdict must be one of PASS, WARN, or FAIL")
        if not isinstance(self.hard_rules_passed, int) or isinstance(
            self.hard_rules_passed, bool
        ):
            raise TypeError("hard_rules_passed must be an integer")
        if not isinstance(self.hard_rules_total, int) or isinstance(
            self.hard_rules_total, bool
        ):
            raise TypeError("hard_rules_total must be an integer")
        if self.hard_rules_total <= 0:
            raise ValueError("hard_rules_total must be greater than zero")
        if not 0 <= self.hard_rules_passed <= self.hard_rules_total:
            raise ValueError(
                "hard_rules_passed must be between zero and hard_rules_total"
            )

        if self.verdict == "PASS":
            self._validate_pass()
        elif self.verdict == "WARN":
            self._validate_warn()
        else:
            self._validate_fail()

    def _validate_pass(self) -> None:
        if self.severity != "info":
            raise ValueError("PASS verdicts must have info severity")
        if self.risk is not None:
            raise ValueError("PASS verdicts must not include a risk")
        if self.hard_rules_passed != self.hard_rules_total:
            raise ValueError("PASS verdicts must pass every hard rule")

    def _validate_warn(self) -> None:
        if self.severity != "warning":
            raise ValueError("WARN verdicts must have warning severity")
        self._validate_nonempty_risk()
        if self.hard_rules_passed != self.hard_rules_total:
            raise ValueError("WARN verdicts must pass every hard rule")

    def _validate_fail(self) -> None:
        if self.agent not in {"security", "cost"}:
            raise ValueError("only security and cost may emit FAIL verdicts")
        if self.severity != "blocker":
            raise ValueError("FAIL verdicts must have blocker severity")
        self._validate_nonempty_risk()
        if self.hard_rules_passed >= self.hard_rules_total:
            raise ValueError("FAIL verdicts must leave at least one hard rule unmet")

    def _validate_nonempty_risk(self) -> None:
        if not isinstance(self.risk, str) or not self.risk.strip():
            raise ValueError("WARN and FAIL verdicts must include a non-empty risk")

    @property
    def is_blocker(self) -> bool:
        """Return whether this verdict is a supported convergence blocker."""
        return (
            self.verdict == "FAIL"
            and self.severity == "blocker"
            and self.agent in {"security", "cost"}
        )


class RejectedCandidate(TypedDict):
    """A candidate rejected before the final consensus result."""

    candidate: ArchitectureCandidate
    rejected_round: int
    reasons: List[str]


@dataclass
class ConsensusResult:
    """The complete output consumed by the ADR adapter."""

    architecture: ArchitectureCandidate
    verdicts: List[AgentVerdict]
    accepted_risks: List[str] = field(default_factory=list)
    unresolved_risks: List[str] = field(default_factory=list)
    rejected: List[RejectedCandidate] = field(default_factory=list)
    round_reached: int = 0
    confidence: int = 0
    forced: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.architecture, dict):
            raise TypeError("architecture must be a dictionary in this increment")
        if not isinstance(self.verdicts, list) or not self.verdicts or not all(
            isinstance(verdict, AgentVerdict) for verdict in self.verdicts
        ):
            raise TypeError("verdicts must be a non-empty list of AgentVerdict instances")
        if not isinstance(self.round_reached, int) or isinstance(
            self.round_reached, bool
        ) or not 0 <= self.round_reached <= 2:
            raise ValueError("round_reached must be an integer between 0 and 2")
        if not isinstance(self.confidence, int) or isinstance(self.confidence, bool):
            raise TypeError("confidence must be an integer")
        if not 0 <= self.confidence <= 100:
            raise ValueError("confidence must be between 0 and 100")
        if not isinstance(self.forced, bool):
            raise TypeError("forced must be a boolean")

        _validate_risks("accepted_risks", self.accepted_risks)
        _validate_risks("unresolved_risks", self.unresolved_risks)
        expected_accepted = _risks_from(self.verdicts, blockers=False)
        if self.accepted_risks != expected_accepted:
            raise ValueError("accepted_risks must match WARN risks in appearance order")

        blockers = _risks_from(self.verdicts, blockers=True)
        if self.forced:
            if self.round_reached != 2:
                raise ValueError("forced delivery is only valid in round 2")
            if not blockers:
                raise ValueError("forced delivery requires at least one blocker")
            if self.unresolved_risks != blockers:
                raise ValueError("unresolved_risks must match blocker risks")
        else:
            if blockers:
                raise ValueError("a result with blockers must be forced")
            if self.unresolved_risks:
                raise ValueError("unresolved_risks require forced delivery")

        if not isinstance(self.rejected, list):
            raise TypeError("rejected must be a list of RejectedCandidate entries")
        if len(self.rejected) != self.round_reached:
            raise ValueError("rejected entries must match the number of re-proposals")
        for expected_round, entry in enumerate(self.rejected):
            _validate_rejected_candidate(entry, expected_round)


class GraphState(TypedDict):
    """State contract used by the bounded orchestrator."""

    context: ProblemContext
    candidate: ArchitectureCandidate
    verdicts: List[AgentVerdict]
    round: int
    rejected: List[RejectedCandidate]
    result: Optional[ConsensusResult]


def _risks_from(verdicts: List[AgentVerdict], *, blockers: bool) -> List[str]:
    risks: List[str] = []
    for verdict in verdicts:
        include = verdict.is_blocker if blockers else verdict.verdict == "WARN"
        if include:
            assert verdict.risk is not None
            if verdict.risk not in risks:
                risks.append(verdict.risk)
    return risks


def _validate_risks(name: str, risks: List[str]) -> None:
    if not isinstance(risks, list) or not all(
        isinstance(risk, str) and risk.strip() for risk in risks
    ):
        raise TypeError("{} must be a list of non-empty strings".format(name))
    if len(set(risks)) != len(risks):
        raise ValueError("{} must not contain duplicates".format(name))


def _validate_rejected_candidate(
    entry: RejectedCandidate, expected_round: int
) -> None:
    if not isinstance(entry, dict):
        raise TypeError("rejected entries must be dictionaries")
    candidate = entry.get("candidate")
    rejected_round = entry.get("rejected_round")
    reasons = entry.get("reasons")
    if not isinstance(candidate, dict):
        raise TypeError("rejected candidate must be a dictionary")
    if not isinstance(rejected_round, int) or isinstance(rejected_round, bool):
        raise TypeError("rejected_round must be an integer")
    if rejected_round != expected_round:
        raise ValueError("rejected entries must be ordered by rejected_round")
    _validate_risks("reasons", reasons)
