import datetime
import io
import tempfile

import yaml
from django.core.management import call_command
from django.test import TestCase

from apps.events.models import Event, EventStatus
from .models import Venue


class MergeVenuesTests(TestCase):
    def setUp(self):
        self.keep = Venue.objects.create(name='The Contemporary', address='25 W. 4th Street', city='Dayton')
        self.dup = Venue.objects.create(name='The Contemporary Dayton', address='25 W 4th Street',
                                        city='Dayton', zip_code='45402', website='https://codayton.org')
        self.event = Event.objects.create(title='Show', start_date=datetime.date(2026, 1, 1),
                                          description='x', status=EventStatus.APPROVED, venue=self.dup)
        self.plan = {'merges': [{
            'keep': 'The Contemporary',
            'absorb': ['The Contemporary Dayton'],
            'set': {'name': 'The Contemporary Dayton', 'address': '25 W. 4th St.'},
        }]}

    def run_plan(self, plan=None, **opts):
        with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False) as fh:
            yaml.safe_dump(plan or self.plan, fh)
        call_command('merge_venues', fh.name, stdout=io.StringIO(), **opts)

    def test_dry_run_changes_nothing(self):
        self.run_plan(dry_run=True)
        self.assertEqual(Venue.objects.count(), 2)
        self.event.refresh_from_db()
        self.assertEqual(self.event.venue, self.dup)

    def test_merge_moves_events_fills_gaps_and_deletes(self):
        old_slug = self.keep.slug
        self.run_plan()
        self.assertEqual(Venue.objects.count(), 1)
        v = Venue.objects.get()
        self.assertEqual(v.pk, self.keep.pk)
        self.assertEqual(v.slug, old_slug)                     # URL unchanged
        self.assertEqual(v.name, 'The Contemporary Dayton')
        self.assertEqual(v.address, '25 W. 4th St.')
        self.assertEqual(v.zip_code, '45402')                   # filled from duplicate
        self.assertEqual(v.website, 'https://codayton.org')
        self.event.refresh_from_db()
        self.assertEqual(self.event.venue, v)

    def test_falls_back_to_absorb_when_keep_missing(self):
        self.keep.delete()
        self.run_plan()
        v = Venue.objects.get()
        self.assertEqual(v.pk, self.dup.pk)
        self.assertEqual(v.name, 'The Contemporary Dayton')

    def test_missing_everything_is_skipped(self):
        self.run_plan({'merges': [{'keep': 'Nope', 'absorb': ['Nada']}]})
        self.assertEqual(Venue.objects.count(), 2)
