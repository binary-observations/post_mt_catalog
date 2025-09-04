#!/usr/bin/env python3
"""
Get_Coords.py

Pass a list of SIMBAD object names via command-line → batch query → J2000 RA/Dec in decimal degrees
plus 1σ errors on RA and Dec (in degrees), derived from the SIMBAD error ellipse.
Prints out Python dicts with [err-, value, err+] arrays for RA and Dec.
"""

import math
import argparse
from astroquery.simbad import Simbad
import astropy.units as u

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

    col_maj   = colmap['coo_err_maj']
    col_min   = colmap['coo_err_min']
    col_angle = colmap['coo_err_angle']
    mainid    = colmap.get('main_id')

    out = []
    for i, row in enumerate(tbl):
        name = row[mainid].decode('utf-8') if mainid and isinstance(row[mainid], bytes) else row[mainid] if mainid else names[i]

        ra_deg  = row[col_ra]  * u.deg
        dec_deg = row[col_dec] * u.deg

        a      = (row[col_maj] * u.arcsec).to(u.deg).value
        b      = (row[col_min] * u.arcsec).to(u.deg).value
        pa_rad = (row[col_angle] * u.deg).to(u.rad).value
        dec_rad = dec_deg.to(u.rad).value

        sigma_dec  = math.hypot(a * math.cos(pa_rad), b * math.sin(pa_rad))
        sigma_east = math.hypot(a * math.sin(pa_rad), b * math.cos(pa_rad))
        sigma_ra   = sigma_east / math.cos(dec_rad)

        out.append({
            'name':     name,
            'ra':       ra_deg.value,
            'dec':      dec_deg.value,
            'err_ra':   sigma_ra,
            'err_dec':  sigma_dec
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
        print(f"{varname} = {{")
        print(f"    \"System Name\": '{o['name']}',")
        print(f"    \"RA\":  [{o['err_ra']:.8f}, {o['ra']:.6f}, {o['err_ra']:.8f}],")
        print(f"    \"Dec\": [{o['err_dec']:.8f}, {o['dec']:.6f}, {o['err_dec']:.8f}],")
        print("}\n")

if __name__ == "__main__":
    main()
