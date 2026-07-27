"""AI Solution Architect MVP domain package."""

from .capability import RECOMMENDED_THRESHOLD, capability_matrix
from .models import (
    ArchitectureCandidate,
    ArchitectureDecisionRecord,
    CapabilityEntry,
    Constraints,
    HardwareProfile,
    ProblemContext,
    RejectedAlternative,
)

__all__ = [
    "ArchitectureCandidate",
    "ArchitectureDecisionRecord",
    "CapabilityEntry",
    "Constraints",
    "HardwareProfile",
    "ProblemContext",
    "RECOMMENDED_THRESHOLD",
    "RejectedAlternative",
    "capability_matrix",
]
