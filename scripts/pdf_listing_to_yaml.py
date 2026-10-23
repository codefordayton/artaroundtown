"""Convert the "Dayton Art Galleries <year>" PDF into an editable YAML listing.

The PDF is a hand-written directory: each gallery is a block of lines (name,
website, street address, city/state/zip, phone), followed by blocks for its
current exhibitions (title, optional subtitle lines, a date line). This script
uses heuristics to turn that into data/galleries_<year>.yaml, which is the
real source for `manage.py import_listing`.

The heuristics are deliberately simple. ALWAYS review the YAML before
importing: wrapped titles, sub-galleries, and odd date phrasing need a human.

Usage:
    python scripts/pdf_listing_to_yaml.py "path/to/listing.pdf" [--as-of YYYY-MM-DD] [--out data/galleries_2026.yaml]

Requires `pdftotext` (poppler) on PATH and PyYAML.
"""
import argparse
import datetime as dt
import re
import subprocess
import sys

import yaml

MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})
MONTHS["sept"] = 9

MONTH_RE = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
TOKEN_RE = re.compile(rf"\b({MONTH_RE})\s+(\d{{1,2}})(?:\s*,?\s*(\d{{4}}))?", re.I)
# "October 7-31, 2026" / "OCTOBER 2–30, 2026": one month, two days
SAME_MONTH_RE = re.compile(rf"\b({MONTH_RE})\s+(\d{{1,2}})\s*[-–—]\s*(\d{{1,2}})(?:\s*,?\s*(\d{{4}}))?", re.I)
DATE_LINE_RE = re.compile(rf"\b(through|{MONTH_RE}\s+\d{{1,2}})\b", re.I)

URL_RE = re.compile(r"https?://\S+", re.I)
STREET_RE = re.compile(r"^\d{1,5}[A-Z]?\s+[A-Za-z#.]")
CITY_RE = re.compile(r"^(.+?),?\s+(OH|Ohio|Oh)\.?\s+(\d{5})(?:-\d{4})?\s*$")
PHONE_RE = re.compile(r"^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]\d{4}$")
ROOM_RE = re.compile(r"^(?:Gallery \d+|(?:North|South|East|West) Gallery|[A-Z][\w.&' ]{2,40} Gallery)$")
PAGE_HEADER_RE = re.compile(r"^\s*Dayton Art Galleries \d{4}\s*$")
PAGE_NUM_RE = re.compile(r"^\s*\d{1,2}\s*$")


def month_num(tok):
    return MONTHS.get(tok.lower().rstrip(".")[:4]) or MONTHS.get(tok.lower().rstrip(".")[:3])


def infer_year(month, as_of):
    """No explicit year: assume the listing's year, rolling into next year
    for months well before the as-of month (a Jan show in an Oct listing)."""
    if month < as_of.month - 1:
        return as_of.year + 1
    return as_of.year


def parse_dates(line, as_of):
    """Return (start, end, note). Either date may be None."""
    note = ""
    m = re.search(r"\(([^)]*)\)", line)
    if m:
        note = m.group(1).strip()
        line = line[:m.start()] + line[m.end():]
    through = bool(re.match(r"\s*through\b", line, re.I))

    sm = SAME_MONTH_RE.search(line)
    if sm:
        mon = month_num(sm.group(1))
        year = int(sm.group(4)) if sm.group(4) else infer_year(mon, as_of)
        return dt.date(year, mon, int(sm.group(2))), dt.date(year, mon, int(sm.group(3))), note

    toks = [(month_num(a), int(b), int(c) if c else None) for a, b, c in TOKEN_RE.findall(line)]
    toks = [t for t in toks if t[0]]
    if not toks:
        return None, None, note
    # Back-fill years: a token without a year borrows from the next one,
    # stepping back a year if its month is later in the calendar.
    for i in range(len(toks) - 2, -1, -1):
        mon, day, year = toks[i]
        if year is None and toks[i + 1][2] is not None:
            nxt_mon, _, nxt_year = toks[i + 1]
            toks[i] = (mon, day, nxt_year - 1 if mon > nxt_mon else nxt_year)
    toks = [(m_, d, y if y else infer_year(m_, as_of)) for m_, d, y in toks]
    dates = []
    for m_, d, y in toks:
        try:
            dates.append(dt.date(y, m_, d))
        except ValueError:
            pass
    if not dates:
        return None, None, note
    if through:
        return None, dates[0], note
    if len(dates) == 1:
        return dates[0], None, note
    return dates[0], dates[-1], note


def clean_lines(text):
    out = []
    for raw in text.splitlines():
        line = raw.replace("​", "").replace("\xa0", " ").rstrip()
        if PAGE_HEADER_RE.match(line) or PAGE_NUM_RE.match(line) or line.strip() == "\f":
            line = ""
        out.append(line.strip("\f").strip())
    return out


def blocks(lines):
    cur = []
    for line in lines:
        if line:
            cur.append(line)
        elif cur:
            yield cur
            cur = []
    if cur:
        yield cur


def is_venue_block(b):
    """A venue block has a postal address and no exhibition dates. A bare
    street-looking line ("16 Galleries", "3D media") isn't enough on its
    own; it needs a city/zip line, a URL, or a phone number alongside."""
    if any(DATE_LINE_RE.search(l) and not URL_RE.search(l) for l in b):
        return False
    has_city = any(CITY_RE.match(l) for l in b)
    has_street = any(STREET_RE.match(l) for l in b)
    has_contact = any(URL_RE.fullmatch(l) or PHONE_RE.match(l) for l in b)
    return has_city or (has_street and has_contact)


def parse_venue(b):
    v = {"name": b[0], "website": "", "address": "", "city": "", "state": "OH",
         "zip": "", "phone": "", "links": [], "notes": [], "shows": []}
    addr = []
    for line in b[1:]:
        if URL_RE.fullmatch(line):
            v["website"] = line
        elif PHONE_RE.match(line):
            v["phone"] = line
        elif CITY_RE.match(line):
            m = CITY_RE.match(line)
            v["city"], v["zip"] = m.group(1).rstrip(",").strip(), m.group(3)
        elif line.lower() in ("website and info",):
            continue
        else:
            addr.append(line)
    v["address"] = ", ".join(addr)
    return v


def merge_wrapped(lines):
    """Re-join a title wrapped onto a second short line by the PDF."""
    out = []
    for line in lines:
        if out and len(out[-1]) > 55 and len(line.split()) <= 3 \
                and not DATE_LINE_RE.search(line) and not ROOM_RE.match(line) \
                and not URL_RE.search(line):
            out[-1] += " " + line
        else:
            out.append(line)
    return out


def parse_show(b, as_of):
    b = merge_wrapped(b)
    date_idx = next(i for i, l in enumerate(b) if DATE_LINE_RE.search(l) and not URL_RE.search(l))
    start, end, note = parse_dates(b[date_idx], as_of)
    rest = [l for i, l in enumerate(b) if i != date_idx]
    url = next((l for l in rest if URL_RE.fullmatch(l)), "")
    rest = [l for l in rest if l != url]
    room = next((l for l in rest if ROOM_RE.match(l)), "")
    rest = [l for l in rest if l != room]
    title = rest[0] if rest else b[0]
    desc = list(rest[1:])
    if room:
        desc.append(f"Location: {room}")
    if note:
        desc.append(note)
    return {"title": title, "start": start, "end": end, "url": url,
            "description": "\n".join(desc)}


def parse(text, as_of):
    venues, current = [], None
    for b in blocks(clean_lines(text)):
        if is_venue_block(b):
            current = parse_venue(b)
            venues.append(current)
        elif current is None:
            continue  # title page
        elif any(DATE_LINE_RE.search(l) and not URL_RE.search(l) for l in b):
            current["shows"].append(parse_show(b, as_of))
        elif len(b) == 2 and URL_RE.fullmatch(b[1]):
            current["links"].append({"label": b[0].rstrip(":"), "url": b[1]})
        elif len(b) == 1 and URL_RE.fullmatch(b[0]):
            current["links"].append({"label": "More info", "url": b[0]})
        else:
            current["notes"].append(" ".join(b))
    return venues


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("pdf")
    ap.add_argument("--as-of", default=dt.date.today().isoformat(),
                    help="Date the listing reflects; used as the start of 'Through ...' shows")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    as_of = dt.date.fromisoformat(args.as_of)
    out = args.out or f"data/galleries_{as_of.year}.yaml"

    text = subprocess.run(["pdftotext", "-layout", args.pdf, "-"],
                          check=True, capture_output=True, text=True).stdout
    venues = parse(text, as_of)
    doc = {"source": args.pdf.split("/")[-1], "as_of": as_of, "venues": venues}
    with open(out, "w") as fh:
        yaml.safe_dump(doc, fh, sort_keys=False, allow_unicode=True, width=100)
    shows = sum(len(v["shows"]) for v in venues)
    print(f"Wrote {out}: {len(venues)} venues, {shows} shows. Review it before importing.", file=sys.stderr)


if __name__ == "__main__":
    main()
