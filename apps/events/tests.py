import datetime

from django.test import TestCase
from django.urls import reverse

from apps.venues.models import Venue
from .forms import EventSubmissionForm
from .models import Event, EventCategory, EventStatus


def make_event(**kw):
    defaults = dict(
        title='Test Show',
        start_date=datetime.date(2026, 11, 5),
        description='A show.',
        status=EventStatus.APPROVED,
        category=EventCategory.VISUAL_ARTS,
        location_name='Somewhere, Dayton',
    )
    defaults.update(kw)
    return Event.objects.create(**defaults)


class CalendarFeedTests(TestCase):
    def setUp(self):
        self.show = make_event(title='Long Show', start_date=datetime.date(2026, 9, 25),
                               end_date=datetime.date(2027, 1, 23))
        self.gig = make_event(title='Gig', category=EventCategory.MUSIC,
                              start_date=datetime.date(2026, 11, 12))
        make_event(title='Pending', status=EventStatus.PENDING)

    def feed(self, **params):
        return self.client.get(reverse('api-events-calendar'), params).json()

    def test_only_approved(self):
        titles = {e['title'] for e in self.feed()}
        self.assertEqual(titles, {'Long Show', 'Gig'})

    def test_category_filter_single_and_list(self):
        self.assertEqual([e['title'] for e in self.feed(category='music')], ['Gig'])
        self.assertEqual(len(self.feed(category='music,visual_arts')), 2)
        self.assertEqual(self.feed(category='dance'), [])

    def test_multi_month_show_appears_in_later_month(self):
        # November view: the show started in September but is still open
        titles = {e['title'] for e in self.feed(start='2026-11-01T00:00:00', end='2026-12-01T00:00:00')}
        self.assertIn('Long Show', titles)
        self.assertIn('Gig', titles)
        # February: the show has closed
        self.assertEqual(self.feed(start='2027-02-01T00:00:00', end='2027-03-01T00:00:00'), [])

    def test_end_is_exclusive_and_color_present(self):
        row = next(e for e in self.feed() if e['title'] == 'Long Show')
        self.assertEqual(row['end'], '2027-01-24')
        self.assertEqual(row['extendedProps']['category'], 'visual_arts')
        self.assertTrue(row['color'].startswith('#'))
        gig = next(e for e in self.feed() if e['title'] == 'Gig')
        self.assertIsNone(gig['end'])


class SubmissionFormTests(TestCase):
    def base_data(self):
        return {
            'title': 'New Concert', 'start_date': '2026-12-01',
            'description': 'Music!', 'location_name': 'Levitt Pavilion',
        }

    def test_category_required(self):
        form = EventSubmissionForm(self.base_data())
        self.assertFalse(form.is_valid())
        self.assertIn('category', form.errors)

    def test_valid_with_category(self):
        data = self.base_data() | {'category': 'music'}
        form = EventSubmissionForm(data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().category, EventCategory.MUSIC)

    def test_submit_page_lists_categories(self):
        resp = self.client.get(reverse('submit-event'))
        self.assertContains(resp, 'name="category"')
        self.assertContains(resp, 'Theater')


class EventPageTests(TestCase):
    def setUp(self):
        self.venue = Venue.objects.create(name='The Co', address='25 W. 4th St.', city='Dayton', zip_code='45402')
        self.event = make_event(title='Semi; colon, comma', venue=self.venue, location_name='',
                                end_date=datetime.date(2026, 11, 7),
                                description='Line one\nLine two')

    def test_detail_has_link_preview_tags(self):
        resp = self.client.get(self.event.get_absolute_url())
        self.assertContains(resp, 'property="og:title" content="Semi; colon, comma')
        self.assertContains(resp, 'property="og:image" content="http://testserver/static/img/og-default.png"')
        self.assertContains(resp, 'name="twitter:card"')
        self.assertContains(resp, 'calendar.google.com/calendar/render')
        self.assertContains(resp, reverse('event-ics', args=[self.event.slug]))

    def test_home_has_default_preview_and_partners(self):
        resp = self.client.get(reverse('home'))
        self.assertContains(resp, 'og:image')
        self.assertContains(resp, 'Code for Dayton')
        self.assertContains(resp, 'The Collaboratory')
        self.assertNotContains(resp, 'aat-dsa-banner')

    def test_ics_all_day_event(self):
        resp = self.client.get(reverse('event-ics', args=[self.event.slug]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/calendar; charset=utf-8')
        body = resp.content.decode()
        self.assertIn('DTSTART;VALUE=DATE:20261105', body)
        self.assertIn('DTEND;VALUE=DATE:20261108', body)        # exclusive end
        self.assertIn('SUMMARY:Semi\; colon\\, comma', body)
        self.assertIn('DESCRIPTION:Line one\\nLine two', body)
        self.assertIn('LOCATION:The Co\\, 25 W. 4th St.\\, Dayton\\, OH 45402', body)
        self.assertTrue(body.endswith('END:VCALENDAR\r\n'))

    def test_ics_timed_event(self):
        ev = make_event(title='Talk', start_time=datetime.time(19, 0), end_time=datetime.time(20, 30))
        body = self.client.get(reverse('event-ics', args=[ev.slug])).content.decode()
        self.assertIn('DTSTART;TZID=America/New_York:20261105T190000', body)
        self.assertIn('DTEND;TZID=America/New_York:20261105T203000', body)

    def test_ics_hidden_for_pending(self):
        ev = make_event(title='Hidden', status=EventStatus.PENDING)
        self.assertEqual(self.client.get(reverse('event-ics', args=[ev.slug])).status_code, 404)

    def test_calendar_page_filters(self):
        resp = self.client.get(reverse('calendar'))
        self.assertContains(resp, 'data-category="music"')
        resp = self.client.get(reverse('calendar-embed'))
        self.assertContains(resp, 'data-category="dance"')

    def test_favicon_redirect(self):
        resp = self.client.get('/favicon.ico')
        self.assertEqual(resp.status_code, 301)
        self.assertIn('favicon.ico', resp['Location'])
