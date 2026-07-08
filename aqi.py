#!/usr/bin/env python3
"""
aqi-cli: fetch PM2.5 from OpenAQ, convert to US EPA AQI, print it colored.

    export OPENAQ_API_KEY=...
    python aqi.py --lat 40.08 --lon -82.80

    python aqi.py --demo        # offline, uses a canned response

Standard library only. Needs an OpenAQ v3 API key (free, openaq.org).
"""

import argparse
import json
import os
import urllib.request
import urllib.error

API = "https://api.openaq.org/v3/locations"

# EPA AQI breakpoints for PM2.5, 24-hour average, ug/m^3.
# Updated per the 2024 revision to the annual PM2.5 NAAQS.
# (C_low, C_high, I_low, I_high, category, ansi_color)
PM25_BREAKPOINTS = [
    (0.0, 9.0, 0, 50, "Good", "\033[92m"),
    (9.1, 35.4, 51, 100, "Moderate", "\033[93m"),
    (35.5, 55.4, 101, 150, "Unhealthy for Sensitive Groups", "\033[33m"),
    (55.5, 125.4, 151, 200, "Unhealthy", "\033[91m"),
    (125.5, 225.4, 201, 300, "Very Unhealthy", "\033[95m"),
    (225.5, 325.4, 301, 500, "Hazardous", "\033[35m"),
]
RESET = "\033[0m"


def pm25_to_aqi(conc):
    """
    EPA piecewise-linear AQI. Concentration is truncated to 1 decimal
    place BEFORE lookup -- this is required by the EPA method, not a
    rounding convenience. A raw 9.04 is Good; without truncation you'd
    compute it as Moderate.
    """
    c = int(conc * 10) / 10.0

    for c_lo, c_hi, i_lo, i_hi, cat, color in PM25_BREAKPOINTS:
        if c_lo <= c <= c_hi:
            aqi = (i_hi - i_lo) / (c_hi - c_lo) * (c - c_lo) + i_lo
            return round(aqi), cat, color

    if c > 325.4:
        return 500, "Beyond AQI", "\033[35m"
    raise ValueError(f"negative concentration: {conc}")


def fetch(lat, lon, radius_m=25000, key=None):
    """Query OpenAQ v3 for PM2.5 sensors near a point."""
    if not key:
        raise SystemExit(
            "No API key. Set OPENAQ_API_KEY, or run with --demo.\n"
            "Free key at https://openaq.org"
        )

    url = f"{API}?coordinates={lat},{lon}&radius={radius_m}&parameters_id=2&limit=10"
    req = urllib.request.Request(url, headers={"X-API-Key": key})

    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"OpenAQ returned {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise SystemExit(f"network error: {e.reason}")


DEMO_RESPONSE = {
    "results": [
        {
            "name": "Columbus - Fairgrounds",
            "coordinates": {"latitude": 39.99, "longitude": -82.99},
            "sensors": [{"parameter": {"name": "pm25"}, "latest": {"value": 8.7}}],
        },
        {
            "name": "New Albany",
            "coordinates": {"latitude": 40.08, "longitude": -82.80},
            "sensors": [{"parameter": {"name": "pm25"}, "latest": {"value": 21.3}}],
        },
        {
            "name": "Wildfire Smoke Test Station",
            "coordinates": {"latitude": 40.10, "longitude": -82.75},
            "sensors": [{"parameter": {"name": "pm25"}, "latest": {"value": 158.0}}],
        },
    ]
}


def extract(payload):
    """Pull (station, pm25) pairs out of the response. Skip anything missing."""
    out = []
    for loc in payload.get("results", []):
        for s in loc.get("sensors", []):
            if s.get("parameter", {}).get("name") != "pm25":
                continue
            val = s.get("latest", {}).get("value")
            if val is None:
                continue
            out.append((loc.get("name", "unnamed"), float(val)))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lat", type=float, default=40.08)
    p.add_argument("--lon", type=float, default=-82.80)
    p.add_argument("--radius", type=int, default=25000, help="meters")
    p.add_argument("--demo", action="store_true", help="offline canned data")
    p.add_argument("--no-color", action="store_true")
    args = p.parse_args()

    payload = DEMO_RESPONSE if args.demo else fetch(
        args.lat, args.lon, args.radius, os.environ.get("OPENAQ_API_KEY")
    )

    readings = extract(payload)
    if not readings:
        print("No PM2.5 sensors found. Try a bigger --radius.")
        return

    print(f"\nPM2.5 near {args.lat}, {args.lon}\n")
    for station, conc in readings:
        aqi, cat, color = pm25_to_aqi(conc)
        if args.no_color:
            color = RESET
        print(f"  {station[:32]:<34}{conc:>6.1f} ug/m3   {color}AQI {aqi:<4}{cat}{RESET}")

    print("\nThese are instantaneous sensor readings, not 24-hour averages.")
    print("The EPA AQI is defined on a 24h mean. Treat these as indicative.")


if __name__ == "__main__":
    main()
