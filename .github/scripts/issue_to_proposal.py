#!/usr/bin/env python3
"""Convert a system-proposal issue into a data/proposed_additions/ JSON file.

Used by .github/workflows/proposal-to-pr.yml. Reads the issue body from
$ISSUE_BODY, extracts the ```json fenced block, validates it against the
catalog conventions (see data/data_schema.json), writes the proposal file,
and reports results via $GITHUB_OUTPUT (valid, error, filename, count).

Validation mirrors the client-side checks in docs/missing_systems.html;
keep the two in sync when the schema changes.
"""
import datetime
import json
import os
import re
import sys

TRIPLET_FIELDS = [
    "Period", "Eccentricity",
    "M1", "M2", "Mass Function", "M1_sin3i", "M2_sin3i",
]

# RA/Dec are scalars in deg; pos_err_mas is the on-sky 1-sigma uncertainty in mas
MAS_PER_DEG = 3.6e6


def set_outputs(**kwargs):
    with open(os.environ.get("GITHUB_OUTPUT", "/dev/stdout"), "a") as fh:
        for key, value in kwargs.items():
            fh.write(f"{key}={str(value).replace(chr(10), ' ')}\n")


def fail(message):
    set_outputs(valid="false", error=message[:2000])
    print(f"Validation failed: {message}")
    sys.exit(0)


def is_finite_or_null(x):
    if x is None:
        return True
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return False
    return x == x and abs(x) != float("inf")


def central_value(value):
    if isinstance(value, list) and len(value) >= 2:
        value = value[1]
    if value is not None and is_finite_or_null(value):
        return value
    return None


def validate_entry(entry, label):
    errors = []
    if not isinstance(entry, dict):
        return [f"{label}: not a JSON object"]

    for key in entry:
        if key.startswith("_"):
            errors.append(
                f'{label}: template field "{key}" left in - delete the example entry')

    name = entry.get("System Name")
    name_ok = (isinstance(name, str) and name.strip()) or (
        isinstance(name, list)
        and any(isinstance(n, str) and n.strip() for n in name))
    if not name_ok:
        errors.append(f'{label}: "System Name" is required')

    for field in TRIPLET_FIELDS:
        value = entry.get(field)
        if value is None:
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            entry[field] = [None, value, None]
            continue
        if not (isinstance(value, list) and len(value) == 3
                and all(is_finite_or_null(x) for x in value)):
            errors.append(
                f'{label}: "{field}" must be a [err-, value, err+] triplet of '
                'plain numbers or null (no unit strings)')

    # Coordinates: scalar deg; legacy [err-, value, err+] triplets are converted,
    # moving their errors (deg) into pos_err_mas
    for field in ("RA", "Dec"):
        value = entry.get(field)
        if isinstance(value, list) and len(value) == 3:
            errs = [x for x in (value[0], value[2])
                    if x is not None and is_finite_or_null(x) and x > 0]
            if errs and entry.get("pos_err_mas") is None:
                entry["pos_err_mas"] = max(errs) * MAS_PER_DEG
            entry[field] = central_value(value)

    ra = central_value(entry.get("RA"))
    dec = central_value(entry.get("Dec"))
    if ra is None or dec is None:
        errors.append(f"{label}: RA and Dec are required as plain numbers (deg)")
    elif not (0 <= ra < 360) or not (-90 <= dec <= 90):
        errors.append(
            f"{label}: RA must be in [0, 360) deg and Dec in [-90, +90] deg")

    pos_err = entry.get("pos_err_mas")
    if pos_err is not None and not (
            isinstance(pos_err, (int, float)) and not isinstance(pos_err, bool)
            and pos_err == pos_err and pos_err >= 0):
        errors.append(
            f'{label}: "pos_err_mas" must be a non-negative number (mas) or null')

    ref = entry.get("Reference")
    if isinstance(ref, str) and ref.strip():
        entry["Reference"] = [ref.strip()]
        ref = entry["Reference"]
    if not (isinstance(ref, list) and ref
            and all(isinstance(r, str) and r.strip() for r in ref)):
        errors.append(
            f'{label}: "Reference" must be a non-empty list of ADS bibcodes')

    notes = entry.get("Notes")
    if not (isinstance(notes, str) and notes.strip()):
        errors.append(
            f'{label}: "Notes" is required (why is this system post-mass-transfer?)')

    return errors


def main():
    body = os.environ.get("ISSUE_BODY", "")
    issue_number = re.sub(r"\D", "", os.environ.get("ISSUE_NUMBER", "0")) or "0"

    match = re.search(r"```json\s*\n(.*?)\n\s*```", body, re.DOTALL)
    if not match:
        fail("No ```json code block found in the issue body.")

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON: {exc}")

    entries = data if isinstance(data, list) else [data]
    if not entries:
        fail("The JSON array is empty.")

    errors = []
    for i, entry in enumerate(entries):
        errors.extend(validate_entry(entry, f"entry {i + 1}"))
    if errors:
        fail(" | ".join(errors))

    first_name = entries[0].get("System Name")
    if isinstance(first_name, list):
        first_name = first_name[0]
    slug = re.sub(r"[^a-z0-9]+", "_", str(first_name).lower()).strip("_")[:60] or "system"
    if len(entries) > 1:
        slug = f"batch_{len(entries)}_systems_{slug}"

    date = datetime.date.today().isoformat()
    filename = f"data/proposed_additions/{date}_issue{issue_number}_{slug}.json"
    # Always write an ARRAY: Combine_and_process_data.py only ingests JSON arrays
    with open(filename, "w") as fh:
        json.dump(entries, fh, indent=2)
        fh.write("\n")

    set_outputs(valid="true", error="", filename=filename, count=len(entries))
    print(f"Wrote {filename} ({len(entries)} system(s))")


if __name__ == "__main__":
    main()
