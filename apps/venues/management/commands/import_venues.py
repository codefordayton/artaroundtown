"""Import venues/galleries from an Essential Arts CSV export.

Expected columns (Wix export): Name, City, Address, URL, Email address.
Idempotent: matches existing venues on name so it can be re-run safely.

Usage:
    python manage.py import_venues path/to/Galleries.csv [--dry-run]
"""
import csv
import re

from django.core.management.base import BaseCommand, CommandError

from apps.venues.models import Venue

ZIP_RE = re.compile(r"\b(\d{5})(?:-\d{4})?\b")


def parse_state(address: str, city: str) -> str:
    # Prefer an explicit ", XX" in the city field (e.g. "Union City, IN")
    if "," in city:
        tail = city.split(",")[-1].strip()
        if len(tail) == 2 and tail.isalpha():
            return tail.upper()
    # Otherwise take the last two-letter token after a comma in the address
    matches = re.findall(r",\s*([A-Za-z]{2})\b", address or "")
    if matches:
        return matches[-1].upper()
    return "OH"


def parse_zip(address: str) -> str:
    m = ZIP_RE.search(address or "")
    return m.group(1) if m else ""


def clean_city(city: str) -> str:
    # "Union City, IN" -> "Union City"; "Lewisburg, Ohio" -> "Lewisburg"
    return city.split(",")[0].strip()


class Command(BaseCommand):
    help = "Import venues from an Essential Arts galleries CSV export."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        try:
            fh = open(opts["path"], newline="", encoding="utf-8-sig")
        except FileNotFoundError:
            raise CommandError(f"File not found: {opts['path']}")

        created = updated = skipped = 0
        with fh:
            reader = csv.DictReader(fh)
            for row in reader:
                name = (row.get("Name") or "").strip()
                if not name:
                    skipped += 1
                    continue

                city_raw = (row.get("City") or "").strip()
                address = (row.get("Address") or "").strip()
                website = (row.get("URL") or "").strip()

                fields = {
                    "city": clean_city(city_raw),
                    "address": address,
                    "state": parse_state(address, city_raw),
                    "zip_code": parse_zip(address),
                    "website": website,
                    "is_active": True,
                }

                if opts["dry_run"]:
                    self.stdout.write(
                        f"  [dry] {name[:40]:42} {fields['city']}, {fields['state']}")
                    continue

                _, was_created = Venue.objects.update_or_create(
                    name=name, defaults=fields)
                created += was_created
                updated += not was_created

        if opts["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"Dry run complete (skipped {skipped})."))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Done. created={created} updated={updated} skipped={skipped}"))
