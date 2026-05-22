import re
import importlib.util
from pathlib import Path

_qf_path = Path(__file__).with_name("quality_flags.py")
_qf_spec = importlib.util.spec_from_file_location("quality_flags", str(_qf_path))
_qf_module = importlib.util.module_from_spec(_qf_spec)
_qf_spec.loader.exec_module(_qf_module)
apply_quality_flag_rules = _qf_module.apply_quality_flag_rules

EVOL_ALLOWED = {"MS","HG","RGB","AGB","He-star","WD","NS","BH"}

def norm_evol(s: str | None):
    if not s:
        return None
    t = s.strip()

    # common normalizations
    if t in ["WD", "white dwarf", "White dwarf"]:
        return "WD"
    if t in ["NS", "neutron star"]:
        return "NS"
    if t in ["BH", "black hole"]:
        return "BH"

    # uncertain MS?
    if t.upper().startswith("MS"):
        return "MS"

    # post AGB -> AGB (if you want strict Table 1)
    if "post" in t.lower() and "agb" in t.lower():
        return "AGB"

    # exact allowed already
    if t in EVOL_ALLOWED:
        return t

    return None

def looks_like_evol(s: str | None):
    return norm_evol(s) is not None

def map_system_class(entry: dict):
    old_class = entry.get("class")
    name = (entry.get("System Name") or "").strip()

    evol1 = entry.get("evol_type_1")
    evol2 = entry.get("evol_type_2")

    # ---- Gaia-specific handling (apply even without legacy class) ----
    if name.startswith("Gaia DR3"):
        # unordered WD + MS
        if {evol1, evol2} == {"MS", "WD"}:
            return "WD + MS"
        else:
            return "Gaia compact-object"

    # If no legacy class, stop here
    if not old_class:
        return None

    c = old_class.strip().lower()

    # ---- Non-Gaia legacy mappings ----
    if "wolf" in c or "rayet" in c:
        return "WR binary"
    if "hot subdwarf" in c or "subdwarf" in c:
        return "Hot subdwarf binary"
    if "post agb" in c:
        return "Post-AGB binary"
    if "barium" in c:
        return "Chemically Peculiar"
    if "neutron" in c:
        return "Radio Pulsar"
    if "white dwarf" in c:
        return "Spectroscopic binary"

    # ---- Fallback ----
    return "Spectroscopic binary"


def upgrade_entry_schema(entry: dict):
    # Remove deprecated field: Detection method for now 
    # (it contains erroneous data, so we're just removing it for now)
    entry.pop("Detection Method", None)

    # do not overwrite if already present
    entry.setdefault("evol_type_1", None)
    entry.setdefault("evol_type_2", None)
    entry.setdefault("obs_type_1", None)
    entry.setdefault("obs_type_2", None)
    entry.setdefault("system_class", None)
    entry.setdefault("quality_flags", [])

    t1 = entry.get("Type1")
    t2 = entry.get("Type2")

    # component 1
    e1 = norm_evol(t1) if isinstance(t1, str) else None
    if e1 and entry["evol_type_1"] is None:
        entry["evol_type_1"] = e1
        # keep the original string if it contained uncertainty or extra info
        if isinstance(t1, str) and t1.strip() != e1 and entry["obs_type_1"] is None:
            entry["obs_type_1"] = t1.strip()
    else:
        if isinstance(t1, str) and entry["obs_type_1"] is None:
            entry["obs_type_1"] = t1.strip()

    # component 2
    e2 = norm_evol(t2) if isinstance(t2, str) else None
    if e2 and entry["evol_type_2"] is None:
        entry["evol_type_2"] = e2
        if isinstance(t2, str) and t2.strip() != e2 and entry["obs_type_2"] is None:
            entry["obs_type_2"] = t2.strip()
    else:
        if isinstance(t2, str) and entry["obs_type_2"] is None:
            entry["obs_type_2"] = t2.strip()

    # ---- NS table entries: enforce evol_type_2 = NS ----
    src = entry.get("source_file")
    if isinstance(src, str) and src.strip().lower() == "ns_table.h5":
        entry["evol_type_2"] = "NS"

    # ---- General rule: RG (Red Giant) obs_type → RGB evol_type ----
    ot1 = entry.get("obs_type_1")
    ot2 = entry.get("obs_type_2")
    if isinstance(ot1, str) and ot1.strip().upper() == "RG":
        entry["evol_type_1"] = "RGB"
    if isinstance(ot2, str) and ot2.strip().upper() == "RG":
        entry["evol_type_2"] = "RGB"

    # ---- Barium stars: ensure proper classification ----
    if isinstance(ot1, str) and ot1.strip().lower() == "barium star":
        # Evolutionary type for the visible (barium) star
        entry["evol_type_1"] = "RGB"
        # Set system class if not already set
        if not entry.get("system_class"):
            entry["system_class"] = "Chemically Peculiar"

    # Escorza 2019 barium stars: enforce Chemically Peculiar + RGB
    if isinstance(src, str) and "barium_stars_Escorza2019" in src:
        entry["evol_type_1"] = "RGB"
        if not entry.get("system_class"):
            entry["system_class"] = "Chemically Peculiar"

    # ---- sgCH and dBa observational types mapping ----
    # sgCH → MS (subgiant branch CH star), dBa → MS (dwarf barium star)
    # Applied AFTER general barium star rules to ensure dwarf/subgiant classifications take precedence
    if isinstance(ot1, str):
        t = ot1.strip().lower()
        if t == "sgch":
            entry["evol_type_1"] = "MS"
        if t == "dba":
            entry["evol_type_1"] = "MS"
    if isinstance(ot2, str):
        t = ot2.strip().lower()
        if t == "sgch":
            entry["evol_type_2"] = "MS"
        if t == "dba":
            entry["evol_type_2"] = "MS"

    # Astrometric WD + MS systems (Shahaf 2024 astrometric orbits)
    if isinstance(src, str) and "WDMS/Shahaf2024.h5" in src:
        entry["system_class"] = "Astrometric WD + MS"
    
    # Spectroscopic WD + MS systems (specific catalogs)
    spectroscopic_wdms = {
        'WDMS/RebassaMansergas2012.h5',
        'WDMS/Zorotovic2010.h5',
        'WDMS/WD_Binary_Pathways_VI.h5',
        'WDMS/WD_Binary_Pathways_X.h5'
    }
    if isinstance(src, str) and src.strip() in spectroscopic_wdms:
        entry["system_class"] = "Spectroscopic WD + MS"
    
    # All other WDMS catalog entries: default to WD + MS systems
    if isinstance(src, str) and "WDMS/" in src:
        if not entry.get("system_class"):
            entry["system_class"] = "WD + MS"
    
    # Escorza 2019 WDMS catalog: override with Chemically Peculiar (barium star + WD systems)
    if isinstance(src, str) and "WDMS/Escorza2019" in src:
        entry["system_class"] = "Chemically Peculiar"

    if (isinstance(ot2, str) and ot2.strip().lower() in {"sdob", "sdb", "hot subdwarf"}) or (isinstance(src, str) and "Be_sdOB_table.h5" in src):
        entry["evol_type_2"] = "He-star"
        entry["evol_type_1"] = "MS"
        if not entry.get("system_class"):
            entry["system_class"] = "Hot subdwarf binary"

    # Wolf-Rayet binaries: WR companion implies He-star + MS primary
    if (isinstance(ot2, str) and "wr" in ot2.strip().lower()) or (isinstance(src, str) and ("WRs_LMC.h5" in src or "WRs_SMC.h5" in src)):
        entry["evol_type_2"] = "He-star"
        entry["evol_type_1"] = "MS"
        entry["system_class"] = "WR binary"

    # Stripped star catalog entries: enforce He-star type and system class
    if isinstance(src, str) and "stripped_star_table.h5" in src:
        entry["evol_type_2"] = "He-star"
        entry["system_class"] = "Intermediate-M stripped star"

    # Blue Straggler catalog entries: enforce system class
    if isinstance(src, str) and "BSS_data.h5" in src:
        entry["system_class"] = "Blue straggler binary"

    # Algols catalog entries: enforce system class
    if isinstance(src, str) and "algols.h5" in src:
        entry["system_class"] = "Algol"

    # Gaia BH binaries: set system class and handle RG → RGB conversion
    name = (entry.get("System Name") or "").strip()
    if "Gaia BH" in name:
        entry["system_class"] = "Astrometric compact object"
        # If obs_type_1 is RG (Red Giant), map to RGB
        if isinstance(ot1, str) and ot1.strip().upper() == "RG":
            entry["evol_type_1"] = "RGB"
    
    # Gaia NS binaries: set system class to Astrometric compact object
    if "Gaia NS" in name:
        if not entry.get("system_class"):
            entry["system_class"] = "Astrometric compact object"
    
    # BH table entries (non-Gaia): set system class to Spectroscopic compact object
    if isinstance(src, str) and "bh_table.h5" in src and "Gaia" not in name:
        if not entry.get("system_class"):
            entry["system_class"] = "Spectroscopic compact object"
    
    # ---- Pulsar binaries: check BEFORE NS table default ----
    # This must come before NS table logic to override the default classification
    notes = entry.get("Notes") or ""
    from_young_psr = isinstance(src, str) and src.strip().lower() == "young_psr_table.h5"
    has_pulsar_in_notes = isinstance(notes, str) and "Pulsar" in notes
    
    if from_young_psr or has_pulsar_in_notes:
        if not entry.get("system_class"):
            entry["system_class"] = "pulsar binary"
    
    # Gaia compact object for specific NS table reference (OJAp 7E..58E)
    # Apply before NS table default to ensure correct classification
    refs = entry.get("Reference")
    has_gaia_ojap_58e = False
    if isinstance(refs, str): # The Gaia NS paper El Badry 2024
        has_gaia_ojap_58e = "2024OJAp....7E..58E" in refs
    elif isinstance(refs, list):
        has_gaia_ojap_58e = any(isinstance(r, str) and "2024OJAp....7E..58E" in r for r in refs)
    if isinstance(src, str) and "ns_table.h5" in src and has_gaia_ojap_58e:
        entry["system_class"] = "Astrometric compact object"
    
    # NS table entries: default system class to Spectroscopic compact object if not set
    if isinstance(src, str) and "ns_table.h5" in src:
        if not entry.get("system_class"):
            entry["system_class"] = "Spectroscopic compact object"

    # ---- Spectroscopic classes → MS (for null evol_type) ----
    # Detect spectral types including combined tokens like "A5+F3p", "B7V+A5V", "O/Be".
    def _is_spectroscopic_class(s):
        if not isinstance(s, str):
            return False
        s = s.strip()
        if not s:
            return False
        # Normalize uncertainty markers (colons) so tokens like 'O9.7: V:' are handled
        s = s.replace(":", " ")
        # If explicit 'Be' designation anywhere as a standalone token
        if re.search(r"\bBe\b", s, re.IGNORECASE):
            return True
        # Split on common separators and inspect tokens
        tokens = re.split(r"[\s,\/\+]+", s)
        for tok in tokens:
            t = tok.strip()
            if not t:
                continue
            # Single-letter spectral class (e.g., "B", "O")
            if re.fullmatch(r"[OBAFGKM]", t, re.IGNORECASE):
                return True
            # Spectral class with optional decimal subtype, optional range (e.g., "B0.5", "B0-1Ve", "O8V", "F3p")
            if re.fullmatch(r"[OBAFGKM][0-9]{0,2}(?:\.[0-9]+)?(?:-[0-9]{1,2})?(?:[A-Za-z]{0,3})?", t, re.IGNORECASE):
                return True
            # Token that is just a luminosity class (e.g., 'V', 'IV'), optionally with emission 'e'
            if re.fullmatch(r"(?:[IVX]{1,3}|V)e?", t, re.IGNORECASE):
                # Only counts if the overall string contains an O/B/A/F/G/K/M letter elsewhere
                if re.search(r"[OBAFGKM]", s, re.IGNORECASE):
                    return True
        return False
    
    if entry["evol_type_1"] is None and _is_spectroscopic_class(entry.get("obs_type_1")):
        entry["evol_type_1"] = "MS"
    
    if entry["evol_type_2"] is None and _is_spectroscopic_class(entry.get("obs_type_2")):
        entry["evol_type_2"] = "MS"

    # ---- Contact binaries: override classification for contact1.h5 ----
    src = entry.get("source_file") or ""
    if isinstance(src, str) and src.strip().lower() == "contact1.h5":
        # Set both evolutionary types to MS
        entry["evol_type_1"] = "MS"
        entry["evol_type_2"] = "MS"
        # Clean obs_type by removing trailing 'Contact' markers
        def _strip_contact(s):
            if not isinstance(s, str):
                return s
            # remove ', Contact' or ', Contact?' (case-insensitive)
            cleaned = re.sub(r"\s*,\s*contact\??$", "", s, flags=re.IGNORECASE)
            return cleaned.strip()
        entry["obs_type_1"] = _strip_contact(entry.get("obs_type_1"))
        entry["obs_type_2"] = _strip_contact(entry.get("obs_type_2"))
        # Force system class
        entry["system_class"] = "Massive contact binary"

    # system class
    if entry["system_class"] is None:
        # Prefer explicit mapping from legacy 'class' field
        sc = map_system_class(entry)
        # If still None or generic, derive from observed types
        if sc is None:
            # If any obs_type indicates 'post AGB', set system_class accordingly
            for s in (entry.get("obs_type_1"), entry.get("obs_type_2")):
                if isinstance(s, str) and "post agb" in s.lower():
                    sc = "Post-AGB binary"
                    break
        # Heuristic: Pulsar binaries
        if sc is None:
            name = (entry.get("System Name") or "").strip()
            evol2 = entry.get("evol_type_2")
            obs2 = entry.get("obs_type_2")
            notes = entry.get("Notes") or ""
            src = entry.get("source_file") or ""
            
            # Check if from young_psr_table.h5
            from_young_psr = isinstance(src, str) and src.strip().lower() == "young_psr_table.h5"
            
            # Check if Notes contains "Pulsar"
            has_pulsar_in_notes = isinstance(notes, str) and "Pulsar" in notes
            
            # Check if system is pulsar-like based on name
            has_ns = (isinstance(obs2, str) and obs2.strip().upper() == "NS") or (evol2 == "NS")
            is_pulsar_like = isinstance(name, str) and name.upper().startswith("PSR")
            
            # Set system_class to "pulsar binary" if any condition is met
            if from_young_psr or has_pulsar_in_notes or (has_ns and is_pulsar_like):
                sc = "pulsar binary"

        # Heuristic: Astrometric compact-object for specific reference
        if sc is None:
            refs = entry.get("Reference")
            target_ref = "2024OJAp....7E..58E"
            has_target_ref = False
            if isinstance(refs, str):
                has_target_ref = (target_ref in refs)
            elif isinstance(refs, list):
                has_target_ref = any(isinstance(r, str) and r == target_ref for r in refs)
            if has_target_ref:
                sc = "Astrometric compact object"
        entry["system_class"] = sc

    # Assign quality flags after all schema/class transformations.
    apply_quality_flag_rules(entry)
        
    return entry
