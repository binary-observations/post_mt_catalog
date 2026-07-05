#!/usr/bin/env python3
"""
Get_Coords_From_SIMBAD.py

Pass a list of SIMBAD object names via command-line → batch query → J2000 RA/Dec
in decimal degrees plus a single on-sky positional uncertainty `pos_err_mas`:
the 1σ semi-major axis of the SIMBAD error ellipse, in milliarcseconds.

mas is SIMBAD's (and Gaia's) native unit for coordinate uncertainties, so no
unit conversion happens here — the unit is still verified against the column
metadata to guard against upstream changes.

Prints Python dicts in the catalog coordinate format:
    "RA": <deg>, "Dec": <deg>, "pos_err_mas": <mas or None>
"""

import argparse
from astroquery.simbad import Simbad
import astropy.units as u
import numpy.ma as ma
import warnings


def get_coords(names):
    custom = Simbad()
    custom.add_votable_fields(
        'ra', 'dec',
        'coo_err_maj',
        'coo_err_min',
        'coo_err_angle'
    )
    tbl = custom.query_objects(names)
    if tbl is None:
        return []

    colmap = {c.lower(): c for c in tbl.colnames}

    for key in ('ra', 'ra(d)', 'ra_d'):
        if key in colmap:
            col_ra = colmap[key]; break
    else:
        raise RuntimeError("No RA column in SIMBAD response")

    for key in ('dec', 'dec(d)', 'dec_d'):
        if key in colmap:
            col_dec = colmap[key]; break
    else:
        raise RuntimeError("No Dec column in SIMBAD response")

    col_maj = colmap['coo_err_maj']
    mainid  = colmap.get('main_id')

    def _angle_unit(col, default):
        unit = tbl[col].unit
        if unit is None:
            warnings.warn(f"SIMBAD column {col!r} has no unit; assuming {default}")
            return default
        try:
            unit.to(u.deg)                      # confirm it's an angular unit
        except u.UnitConversionError:
            raise RuntimeError(f"SIMBAD column {col!r} has non-angular unit {unit}")
        return u.Unit(unit)

    err_unit_maj = _angle_unit(col_maj, u.mas)

    out = []
    for i, row in enumerate(tbl):
        name = row[mainid].decode('utf-8') if mainid and isinstance(row[mainid], bytes) else row[mainid] if mainid else names[i]

        # On-sky positional uncertainty: semi-major axis of the error ellipse.
        # This is the quantity to compare against the 100 mas (0.1 arcsec)
        # deduplication threshold; no per-coordinate projection needed.
        maj = row[col_maj]
        if maj is ma.masked:
            pos_err_mas = None                  # no error ellipse in SIMBAD
        else:
            pos_err_mas = float((maj * err_unit_maj).to(u.mas).value)

        out.append({
            'name':        name,
            'ra_deg':      float(row[col_ra]),
            'dec_deg':     float(row[col_dec]),
            'pos_err_mas': pos_err_mas,
        })
    return out


def main():
    parser = argparse.ArgumentParser(description="Query SIMBAD for object coordinates.")
    parser.add_argument("targets", metavar="TARGET", nargs="+", help="SIMBAD object names")
    args = parser.parse_args()

    coords = get_coords(args.targets)
    if not coords:
        print("No results found. Check your object names?")
        return

    for o in coords:
        varname = o['name'].upper().replace(' ', '_')
        err = 'None' if o['pos_err_mas'] is None else f"{o['pos_err_mas']:.3g}"
        print(f"{varname} = {{")
        print(f"    \"System Name\": '{o['name']}',")
        print(f"    \"RA\": {o['ra_deg']:.7f},")
        print(f"    \"Dec\": {o['dec_deg']:.7f},")
        print(f"    \"pos_err_mas\": {err},")
        print("}\n")

if __name__ == "__main__":
    main()
