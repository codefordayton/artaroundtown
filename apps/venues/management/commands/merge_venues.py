"""Merge duplicate venues and tidy their details, driven by a YAML plan.

Plan format (see data/venue_cleanup.yaml):

    merges:
      - keep: "The Contemporary"            # venue that survives
        absorb: ["The Contemporary Dayton"] # duplicates folded into it
        set:                                # final field values (optional)
          name: "The Contemporary Dayton"
          address: "25 W. 4th Street"
          city: Dayton
          zip_code: "45402"

Names match case-insensitively on the venue name (slugs also accepted).
For each entry: every event on an absorbed venue is moved to the kept
venue, blank fields on the kept venue are filled from the absorbed ones,
`set` values overwrite, then the absorbed venues are deleted. The kept
venue's slug never changes, so existing links keep working. If the `keep`
venue is missing but an `absorb` one exists, that one is kept instead.

Always run with --dry-run first:

    python manage.py merge_venues data/venue_cleanup.yaml --dry-run
    python manage.py merge_venues data/venue_cleanup.yaml
"""
import yaml
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.venues.models import Venue

MERGEABLE_FIELDS = ['address', 'city', 'state', 'zip_code', 'website', 'phone', 'description', 'logo']
SETTABLE_FIELDS = ['name'] + MERGEABLE_FIELDS[:-1]


def find_venue(ident):
    qs = Venue.objects.filter(name__iexact=ident) | Venue.objects.filter(slug=ident)
    matches = list(qs.distinct())
    if len(matches) > 1:
        raise CommandError(f'"{ident}" matches more than one venue: {[v.pk for v in matches]}')
    return matches[0] if matches else None


class Command(BaseCommand):
    help = 'Merge duplicate venues and update their details from a YAML plan.'

    def add_arguments(self, parser):
        parser.add_argument('plan', help='Path to the YAML plan file')
        parser.add_argument('--dry-run', action='store_true', help='Report only; write nothing')

    def handle(self, *args, **opts):
        try:
            with open(opts['plan']) as fh:
                plan = yaml.safe_load(fh) or {}
        except FileNotFoundError:
            raise CommandError(f"Plan not found: {opts['plan']}")

        dry = opts['dry_run']
        entries = plan.get('merges') or []
        if not entries:
            raise CommandError('Plan has no "merges" entries.')

        moved = deleted = updated = 0
        with transaction.atomic():
            for entry in entries:
                result = self.apply(entry, dry)
                if result:
                    m, d, u = result
                    moved += m; deleted += d; updated += u
            if dry:
                transaction.set_rollback(True)

        verb = 'Would move' if dry else 'Moved'
        self.stdout.write(self.style.SUCCESS(
            f'{verb} {moved} event(s), deleted {deleted} duplicate venue(s), '
            f'updated {updated} venue(s).'
        ))
        if dry:
            self.stdout.write('Dry run: nothing was written.')

    def apply(self, entry, dry):
        keep_name = entry.get('keep')
        absorb_names = entry.get('absorb') or []
        updates = {k: v for k, v in (entry.get('set') or {}).items() if k in SETTABLE_FIELDS}
        if not keep_name:
            raise CommandError(f'Entry without "keep": {entry}')

        keep = find_venue(keep_name)
        absorbed = [v for v in (find_venue(n) for n in absorb_names) if v is not None]
        if keep is None and absorbed:
            keep = absorbed.pop(0)
            self.stdout.write(self.style.WARNING(
                f'  "{keep_name}" not found; keeping "{keep.name}" (#{keep.pk}) instead'))
        if keep is None:
            self.stdout.write(self.style.WARNING(
                f'  skip: none of {[keep_name, *absorb_names]} exist'))
            return None
        absorbed = [v for v in absorbed if v.pk != keep.pk]

        label = updates.get('name', keep.name)
        self.stdout.write(f'\n{label}  (keep #{keep.pk} "{keep.name}")')

        moved = 0
        for dup in absorbed:
            n = dup.events.count()
            self.stdout.write(f'  absorb #{dup.pk} "{dup.name}" — {n} event(s), '
                              f'{dup.address or "no address"}')
            if not dry:
                dup.events.update(venue=keep)
            moved += n
            # fill gaps on the kept venue from the duplicate
            for f in MERGEABLE_FIELDS:
                if not getattr(keep, f) and getattr(dup, f):
                    setattr(keep, f, getattr(dup, f))
                    self.stdout.write(f'    fill {f}: {getattr(dup, f)!s:.60}')

        changed = False
        for f, value in updates.items():
            if getattr(keep, f) != value:
                self.stdout.write(f'  set {f}: {getattr(keep, f)!r} -> {value!r}')
                setattr(keep, f, value)
                changed = True
        if not keep.is_active:
            keep.is_active = True
            changed = True

        if not dry:
            keep.save()
            for dup in absorbed:
                dup.delete()
        return moved, len(absorbed), int(changed or bool(absorbed))
