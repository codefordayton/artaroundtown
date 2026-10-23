"""Import venues and their exhibitions from a YAML gallery listing.

The YAML is produced by scripts/pdf_listing_to_yaml.py from the annual
"Dayton Art Galleries" PDF, then hand-reviewed. Format:

    as_of: 2026-10-01          # start date used for "Through <date>" shows
    venues:
      - name: The Contemporary
        website: https://codayton.org
        address: 25 W. 4th Street
        city: Dayton
        state: OH
        zip: "45402"
        phone: 937-224-3822
        category: visual_arts  # optional; default category for this venue's shows
        links:                 # optional; appended to the venue description
          - {label: Events, url: https://codayton.org/events/}
        notes: []              # optional free text, appended to the description
        shows:
          - title: "Ella Kraimer: Appearances"
            start: 2026-09-25  # omit (or null) for "Through ..." shows
            end: 2027-01-23
            url: ""
            description: ""

Idempotent: venues match on name (case-insensitive); shows match on title
plus venue, or title plus start date, so Boomtech-calendar imports of the
same show are updated rather than duplicated. Venue fields in the YAML
overwrite existing values when non-empty; descriptions are only filled when
blank unless --overwrite-descriptions is given.

Usage:
    python manage.py import_listing data/galleries_2026.yaml [--dry-run]
                                    [--as-of YYYY-MM-DD] [--overwrite-descriptions]
"""
import datetime as dt

import yaml
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from apps.events.models import Event, EventCategory, EventStatus
from apps.venues.models import Venue


def compose_description(v):
    parts = [n.strip() for n in (v.get("notes") or []) if n and n.strip()]
    for link in v.get("links") or []:
        if link.get("url"):
            parts.append(f"{link.get('label') or 'More info'}: {link['url']}")
    return "\n\n".join(parts)


def as_date(value, label):
    if value in (None, ""):
        return None
    if isinstance(value, dt.date):
        return value
    try:
        return dt.date.fromisoformat(str(value))
    except ValueError:
        raise CommandError(f"Bad date {value!r} for {label}")


class Command(BaseCommand):
    help = "Import venues and exhibitions from a YAML gallery listing."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--as-of", default=None,
                            help="Override the listing's as_of date")
        parser.add_argument("--overwrite-descriptions", action="store_true",
                            help="Replace existing venue descriptions instead of only filling blanks")

    def handle(self, *args, **opts):
        try:
            with open(opts["path"]) as fh:
                doc = yaml.safe_load(fh) or {}
        except FileNotFoundError:
            raise CommandError(f"File not found: {opts['path']}")

        as_of = as_date(opts["as_of"] or doc.get("as_of"), "as_of") or dt.date.today()
        dry = opts["dry_run"]
        stats = dict(venues_created=0, venues_updated=0,
                     shows_created=0, shows_updated=0, shows_skipped=0)

        for v in doc.get("venues") or []:
            name = (v.get("name") or "").strip()
            if not name:
                continue
            venue = self._upsert_venue(name, v, opts, dry, stats)
            default_cat = v.get("category") or EventCategory.VISUAL_ARTS
            for show in v.get("shows") or []:
                self._upsert_show(show, venue, name, default_cat, as_of, dry, stats)

        style = self.style.WARNING if dry else self.style.SUCCESS
        prefix = "Dry run. Would do: " if dry else "Done. "
        self.stdout.write(style(prefix + ", ".join(f"{k}={n}" for k, n in stats.items())))

    def _upsert_venue(self, name, v, opts, dry, stats):
        fields = {k: (v.get(src) or "").strip() for k, src in (
            ("website", "website"), ("address", "address"), ("city", "city"),
            ("state", "state"), ("zip_code", "zip"), ("phone", "phone"))}
        fields = {k: val for k, val in fields.items() if val}
        fields["is_active"] = True
        description = compose_description(v)

        venue = Venue.objects.filter(name__iexact=name).first()
        if venue is None:
            stats["venues_created"] += 1
            self.stdout.write(f"  + venue {name}")
            if dry:
                return None
            venue = Venue(name=name, city=fields.get("city") or "Dayton", description=description)
            for k, val in fields.items():
                setattr(venue, k, val)
            venue.save()
            return venue

        stats["venues_updated"] += 1
        self.stdout.write(f"  ~ venue {name}")
        if dry:
            return venue
        for k, val in fields.items():
            setattr(venue, k, val)
        if description and (opts["overwrite_descriptions"] or not venue.description.strip()):
            venue.description = description
        venue.save()
        return venue

    def _upsert_show(self, show, venue, venue_name, default_cat, as_of, dry, stats):
        title = (show.get("title") or "").strip()
        start = as_date(show.get("start"), title)
        end = as_date(show.get("end"), title)
        if not title or (start is None and end is None):
            stats["shows_skipped"] += 1
            self.stdout.write(self.style.WARNING(
                f"    ! skipped (no dates): {title or '<untitled>'} @ {venue_name}"))
            return
        if start is None:
            start = min(as_of, end)
        if end is not None and end < start:
            self.stdout.write(self.style.WARNING(
                f"    ! end before start, dropping end: {title}"))
            end = None

        description = (show.get("description") or "").strip() or f"On view at {venue_name}."
        fields = {
            "end_date": end,
            "url": (show.get("url") or "").strip(),
            "description": description,
            "category": show.get("category") or default_cat,
            "status": EventStatus.APPROVED,
            "venue": venue,
        }

        match = Q(title__iexact=title) & (Q(start_date=start) | Q(venue=venue) if venue else Q(start_date=start))
        existing = Event.objects.filter(match).order_by("pk").first()
        verb = "~" if existing else "+"
        self.stdout.write(f"    {verb} {start} → {end or '…'}  {title[:60]}")
        if dry:
            stats["shows_updated" if existing else "shows_created"] += 1
            return
        if existing:
            for k, val in fields.items():
                setattr(existing, k, val)
            existing.start_date = start
            existing.save()
            stats["shows_updated"] += 1
        else:
            Event.objects.create(title=title, start_date=start, **fields)
            stats["shows_created"] += 1
