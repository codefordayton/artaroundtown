from django.conf import settings
from django.db import models
from django.utils.text import slugify


class EventStatus(models.TextChoices):
    PENDING = 'pending', 'Pending Review'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'


class Event(models.Model):
    title = models.CharField(max_length=300)
    slug = models.SlugField(unique=True, blank=True)

    # Submitter info — stored explicitly so it survives account deletion
    submitter_name = models.CharField(max_length=200, blank=True)
    submitter_email = models.EmailField(blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='submitted_events',
    )

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    opening_reception_date = models.DateField(null=True, blank=True)
    opening_reception_time = models.TimeField(null=True, blank=True)

    artist_talk_date = models.DateField(null=True, blank=True)
    artist_talk_time = models.TimeField(null=True, blank=True)

    closing_reception_date = models.DateField(null=True, blank=True)
    closing_reception_time = models.TimeField(null=True, blank=True)

    venue = models.ForeignKey(
        'venues.Venue',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='events',
    )
    # Free-text fallback for events at unlisted locations
    location_name = models.CharField(max_length=300, blank=True)

    url = models.URLField(blank=True)
    description = models.TextField()
    image = models.ImageField(upload_to='events/', blank=True)

    status = models.CharField(
        max_length=20,
        choices=EventStatus.choices,
        default=EventStatus.PENDING,
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_date']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug = base
            n = 1
            while Event.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def display_location(self):
        if self.venue:
            return self.venue.name
        return self.location_name
