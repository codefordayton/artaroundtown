"""Import events from a boomte.ch calendar JSON export.

Reads the JSON produced by scripts/fetch_boom_calendar.py and creates or
updates Event rows. Idempotent: matches existing events on (title, start_date)
so it can be re-run safely. Downloads each event's image into the configured
storage (local media in dev, DigitalOcean Spaces in production).

Usage:
    python manage.py import_calendar [path] [--since YYYY-MM-DD] [--dry-run]
                                     [--no-images] [--force-images]
"""
import datetime
import json
import re
from html import unescape
from html.parser import HTMLParser
from urllib.request import urlopen, Request

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from apps.events.models import Event, EventCategory, EventStatus

CATEGORY_MAP = {
    "visual arts": EventCategory.VISUAL_ARTS,
    "music": EventCategory.MUSIC,
    "theater": EventCategory.THEATER,
    "dance": EventCategory.DANCE,
    "museums": EventCategory.MUSEUMS,
}


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def html_to_text(html: str) -> str:
    if not html:
        return ""
    parser = _TextExtractor()
    parser.feed(html)
    text = unescape("".join(parser.parts))
    # collapse runs of whitespace but keep paragraph breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*", "\n\n", text)
    return text.strip()


def first_url_from_desc(html: str) -> str:
    m = re.search(r'href=["\'](https?://[^"\']+)["\']', html or "")
    return m.group(1) if m else ""


def parse_dt(value: str):
    """'2026-02-13T12:00' -> (date, time or None)."""
    if not value:
        return None, None
    try:
        dt = datetime.datetime.fromisoformat(value)
    except ValueError:
        # date-only
        return datetime.date.fromisoformat(value[:10]), None
    return dt.date(), dt.time()


def image_url_from_field(image_field: str) -> str:
    """The boom `image` field is a JSON array string of URLs."""
    if not image_field:
        return ""
    try:
        urls = json.loads(image_field)
        if isinstance(urls, list) and urls:
            return urls[0]
    except (json.JSONDecodeError, TypeError):
        if image_field.startswith("http"):
            return image_field
    return ""


class Command(BaseCommand):
    help = "Import events from a boomte.ch calendar JSON export."

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", default="data/boom_calendar.json")
        parser.add_argument("--since", default="2025-01-01",
                            help="Skip events starting before this date (YYYY-MM-DD).")
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would happen without writing.")
        parser.add_argument("--no-images", action="store_true",
                            help="Skip downloading event images.")
        parser.add_argument("--force-images", action="store_true",
                            help="Re-download images even if the event already has one.")

    def handle(self, *args, **opts):
        try:
            with open(opts["path"]) as fh:
                data = json.load(fh)
        except FileNotFoundError:
            raise CommandError(f"File not found: {opts['path']}. "
                               "Run scripts/fetch_boom_calendar.py first.")

        since = datetime.date.fromisoformat(opts["since"])
        dry = opts["dry_run"]
        events = data.get("events", [])

        created = updated = skipped = images = 0

        for ev in events:
            start_date, start_time = parse_dt(ev.get("start"))
            if not start_date or start_date < since:
                skipped += 1
                continue

            end_date, end_time = parse_dt(ev.get("end"))
            all_day = bool(ev.get("all_day"))
            single_day = (not end_date) or end_date == start_date

            # Only keep clock times for single-day, timed events; multi-day
            # exhibitions carry meaningless placeholder times.
            if all_day or not single_day:
                start_time = end_time = None
            if single_day:
                end_date = None

            cats = ev.get("categories") or []
            cat_name = (cats[0].get("name") if cats else "").strip().lower()
            category = CATEGORY_MAP.get(cat_name, "")

            desc_html = ev.get("desc") or ""
            description = html_to_text(desc_html)
            url = ev.get("link") or first_url_from_desc(desc_html)
            venue = ev.get("venue") or {}
            location = (venue.get("name") or venue.get("address") or "").strip()

            title = (ev.get("title") or "").strip()
            if not title:
                skipped += 1
                continue

            fields = {
                "category": category,
                "end_date": end_date,
                "start_time": start_time,
                "end_time": end_time,
                "location_name": location,
                "url": url or "",
                "description": description,
                "status": EventStatus.APPROVED,
            }

            if dry:
                self.stdout.write(f"  [dry] {start_date} {title[:50]} "
                                  f"({category or 'uncat'})")
                continue

            obj, was_created = Event.objects.update_or_create(
                title=title, start_date=start_date, defaults=fields,
            )
            created += was_created
            updated += not was_created

            if not opts["no_images"]:
                if self._maybe_download_image(obj, ev, opts["force_images"]):
                    images += 1

        if dry:
            self.stdout.write(self.style.SUCCESS(
                f"Dry run: {len(events)} events in file, "
                f"{skipped} skipped (before {since} or blank)."))
            return

        self.stdout.write(self.style.SUCCESS(
            f"Done. created={created} updated={updated} "
            f"skipped={skipped} images={images}"))

    def _maybe_download_image(self, obj, ev, force):
        if obj.image and not force:
            return False
        src = image_url_from_field(ev.get("image"))
        if not src:
            return False
        try:
            req = Request(src, headers={"User-Agent": "artaroundtown-importer"})
            with urlopen(req, timeout=30) as resp:
                content = resp.read()
        except Exception as exc:  # noqa: BLE001
            self.stderr.write(f"  image failed for {obj.title[:40]}: {exc}")
            return False

        ext = src.split(".")[-1].split("?")[0].lower()
        if ext not in ("jpg", "jpeg", "png", "gif", "webp"):
            ext = "jpg"
        obj.image.save(f"{obj.slug}.{ext}", ContentFile(content), save=True)
        return True
