"""Fetch the Essential Arts (boomte.ch) calendar JSON and save it to disk.

The Essential Arts calendar is a third-party Wix widget backed by
calendar.apiboomtech.com. The widget's data request carries a short-lived
`instance` token, so we load the page with Playwright and capture the
`published_calendar` API response rather than calling the API directly.

Usage:
    python scripts/fetch_boom_calendar.py [--url URL] [--out data/boom_calendar.json]
"""
import argparse
import json
import os
import sys

from playwright.sync_api import sync_playwright

DEFAULT_URL = "https://www.essentialartsdayton.org/calendar"
DEFAULT_OUT = "data/boom_calendar.json"


def fetch(url: str, out: str) -> int:
    captured = {}

    def on_response(resp):
        if "apiboomtech.com/api/published_calendar" in resp.url:
            try:
                captured["data"] = resp.json()
            except Exception as exc:  # noqa: BLE001
                captured["error"] = str(exc)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1600})
        page.on("response", on_response)
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        # Wix widget loads its data a few seconds after the page shell.
        page.wait_for_timeout(9000)
        browser.close()

    data = captured.get("data")
    if not data:
        print(f"ERROR: no calendar data captured ({captured.get('error', 'no response')})",
              file=sys.stderr)
        return 1

    events = data.get("events", [])
    out_dir = os.path.dirname(out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out, "w") as fh:
        json.dump(data, fh, indent=2)
    print(f"Saved {len(events)} events to {out}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--out", default=DEFAULT_OUT)
    raise SystemExit(fetch(*vars(ap.parse_args()).values()))
