"""Quality flag definitions and assignment rules for catalog entries.

This module centralizes:
1) Which flags are valid.
2) Human-readable meaning for each flag.
3) Rule-based assignment by source file, reference, and name pattern.

The main entrypoint is `apply_quality_flag_rules(entry)`.
"""

from __future__ import annotations

from typing import Any


# Canonical flag descriptions. Keep these short and publication-friendly.
QUALITY_FLAG_DEFINITIONS: dict[str, str] = {
    "assumed_e": "Eccentricity was assumed (for example circular by construction).",
    "assumed_M1": "Primary mass M1 was assumed rather than directly measured.",
    "assumed_M2": "Secondary mass M2 was assumed rather than directly measured.",
    "assumed_q": "Mass ratio q was assumed and propagates into M1 and/or M2.",
    "min_M1": "Primary mass M1 is a lower limit.",
    "max_M1": "Primary mass M1 is an upper limit.",
    "min_M2": "Secondary mass M2 is a lower limit.",
    "max_M2": "Secondary mass M2 is an upper limit.",
    "min_P": "Orbital period P is a lower limit.",
    "max_P": "Orbital period P is an upper limit.",
    "min_e": "Eccentricity e is a lower limit.",
    "max_e": "Eccentricity e is an upper limit.",
}

VALID_QUALITY_FLAGS = set(QUALITY_FLAG_DEFINITIONS.keys())


# -----------------------------------------------------------------------------
# Rule configuration
# -----------------------------------------------------------------------------
# Keep this declarative so new rules are one-line additions.
# Rule tuple format: (flag, note)

# Rules applied to all entries from a specific source file in one go
SOURCE_FILE_RULES_EXACT: dict[str, list[tuple[str, str]]] = {
    # Example rule already aligned with current schema logic.
    "contact1.h5": [
        (
            "assumed_e",
            "Contact systems are treated as circular by construction in source table.",
        )
    ],
}

# Match when a source_file string contains a token.
SOURCE_FILE_RULES_CONTAINS: dict[str, list[tuple[str, str]]] = {
    # Add tokens as needed, e.g.:
    # "SomeCatalog2024": [("assumed_M1", "Canonical sdB mass of 0.47-0.50 Msun")],
}

# Rules applied to entries with a specific reference bibcode. Match exact string.
# Match individual reference bibcodes.
REFERENCE_RULES_EXACT: dict[str, list[tuple[str, str]]] = {
    # "2024OJAp....7E..58E": [("min_M2", "Reported companion masses are lower limits")],
}

# Rules applies to Systems with a specific Name prefix.
SYSTEM_NAME_PREFIX_RULES: dict[str, list[tuple[str, str]]] = {
    # "Gaia DR3": [("assumed_q", "Example placeholder")],
}


def _ensure_quality_fields(entry: dict[str, Any]) -> None:
    """Ensure quality flag columns exist and have the expected shape."""
    qf = entry.get("quality_flags")
    if not isinstance(qf, list):
        qf = []
    entry["quality_flags"] = [f for f in qf if isinstance(f, str)]


def _append_to_notes(entry: dict[str, Any], text: str) -> None:
    """Append text to Notes while avoiding duplicate insertions."""
    if not isinstance(text, str) or not text.strip():
        return
    note_text = text.strip()

    current = entry.get("Notes")
    if current in (None, ""):
        entry["Notes"] = note_text
        return

    current_text = str(current)
    if note_text in current_text:
        return
    entry["Notes"] = f"{current_text}; {note_text}"


def add_quality_flag(entry: dict[str, Any], flag: str, note: str | None = None) -> None:
    """Add one quality flag and optional note to an entry.

    Unknown flags are ignored to keep production runs robust.
    """
    if flag not in VALID_QUALITY_FLAGS:
        return

    _ensure_quality_fields(entry)

    flags: list[str] = entry["quality_flags"]
    if flag not in flags:
        flags.append(flag)

    if note:
        _append_to_notes(entry, f"quality_flag[{flag}]: {note}")


def _iter_references(entry: dict[str, Any]) -> list[str]:
    refs = entry.get("Reference")
    if isinstance(refs, str):
        return [refs]
    if isinstance(refs, list):
        return [r for r in refs if isinstance(r, str)]
    return []


def apply_quality_flag_rules(entry: dict[str, Any]) -> dict[str, Any]:
    """Populate quality_flags using declarative source/reference rules."""
    _ensure_quality_fields(entry)

    src = entry.get("source_file")
    if isinstance(src, str):
        src_stripped = src.strip()

        for flag, note in SOURCE_FILE_RULES_EXACT.get(src_stripped, []):
            add_quality_flag(entry, flag, note)

        for token, rules in SOURCE_FILE_RULES_CONTAINS.items():
            if token in src_stripped:
                for flag, note in rules:
                    add_quality_flag(entry, flag, note)

    for ref in _iter_references(entry):
        for flag, note in REFERENCE_RULES_EXACT.get(ref, []):
            add_quality_flag(entry, flag, note)

    name = entry.get("System Name")
    if isinstance(name, str):
        for prefix, rules in SYSTEM_NAME_PREFIX_RULES.items():
            if name.startswith(prefix):
                for flag, note in rules:
                    add_quality_flag(entry, flag, note)

    # Stable output order helps diffs and downstream reproducibility.
    entry["quality_flags"] = sorted(set(entry["quality_flags"]))
    return entry
