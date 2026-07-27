"""Hardware Analyzer that produces the deterministic AI Capability Matrix.

Given a HardwareProfile, it scores each technique (RAG, Agents, LoRA,
Fine-Tuning) from 0 to 100 by comparing available memory against curated
requirement tiers. Scores are reproducible with exact arithmetic.
"""

from __future__ import annotations

from fractions import Fraction
from typing import List

from .kb import TECHNIQUE_REQUIREMENTS, TechniqueRequirement, largest_local_model_for
from .models import CapabilityEntry, HardwareProfile

# A technique is flagged "recommended" at or above this score.
RECOMMENDED_THRESHOLD = 60


def capability_matrix(hardware: HardwareProfile) -> List[CapabilityEntry]:
    """Compute one CapabilityEntry per technique for the given hardware."""
    entries = [
        _score_technique(hardware, requirement)
        for requirement in TECHNIQUE_REQUIREMENTS.values()
    ]
    return entries


def _score_technique(
    hardware: HardwareProfile, requirement: TechniqueRequirement
) -> CapabilityEntry:
    usable = hardware.usable_model_memory_gb()

    if requirement.needs_gpu and not hardware.has_gpu:
        # Training techniques need a real accelerator; unified memory is not
        # enough. Cap the score low but non-zero if there is a lot of RAM.
        score = _round_half_up(Fraction(min(35, int(hardware.ram_gb))))
        return CapabilityEntry(
            technique=requirement.technique,
            score=int(score),
            recommended=False,
            reason="Requiere GPU dedicada; esta máquina no la tiene.",
        )

    if hardware.ram_gb < requirement.min_ram_gb and not requirement.needs_gpu:
        score = _round_half_up(
            Fraction(50 * int(hardware.ram_gb), max(1, int(requirement.min_ram_gb)))
        )
        return CapabilityEntry(
            technique=requirement.technique,
            score=int(min(score, 55)),
            recommended=False,
            reason="RAM insuficiente para un funcionamiento holgado.",
        )

    score = _memory_score(usable, requirement)
    recommended = score >= RECOMMENDED_THRESHOLD
    reason = _reason_for(requirement, usable, recommended)
    return CapabilityEntry(
        technique=requirement.technique,
        score=score,
        recommended=recommended,
        reason=reason,
    )


def _memory_score(usable: float, requirement: TechniqueRequirement) -> int:
    min_req = requirement.min_memory_gb
    rec_req = requirement.recommended_memory_gb
    if usable >= rec_req:
        return 100
    if usable >= min_req and rec_req > min_req:
        # Scale 60..100 between the minimum and recommended memory.
        ratio = Fraction(int(round((usable - min_req) * 100)), int(round((rec_req - min_req) * 100)))
        return int(_round_half_up(Fraction(60) + ratio * 40))
    if min_req > 0:
        # Below the minimum: scale 0..55.
        ratio = Fraction(int(round(usable * 100)), int(round(min_req * 100)))
        return int(_round_half_up(ratio * 55))
    return 100


def _reason_for(
    requirement: TechniqueRequirement, usable: float, recommended: bool
) -> str:
    model = largest_local_model_for(usable)
    model_note = (
        "cabe {}".format(model.name) if model else "no cabe un modelo local relevante"
    )
    if recommended:
        return "Memoria suficiente ({:.0f} GB usables; {}).".format(usable, model_note)
    return "Memoria ajustada ({:.0f} GB usables; {}).".format(usable, model_note)


def _round_half_up(value: Fraction) -> int:
    return (2 * value.numerator + value.denominator) // (2 * value.denominator)
