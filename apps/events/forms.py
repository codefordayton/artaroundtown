from django import forms

from apps.venues.models import Venue
from .models import Event


class EventSubmissionForm(forms.ModelForm):
    submitter_name = forms.CharField(
        max_length=200,
        required=False,
        label='Your name',
    )
    submitter_email = forms.EmailField(
        required=False,
        label='Your email',
        help_text='We may contact you if we have questions about your submission.',
    )

    venue = forms.ModelChoiceField(
        queryset=Venue.objects.filter(is_active=True).order_by('name'),
        required=False,
        empty_label='— Select a gallery / venue —',
        help_text='Choose from our directory, or enter a custom location below.',
    )
    location_name = forms.CharField(
        max_length=300,
        required=False,
        label='Custom location',
        help_text='If the venue is not in our directory, enter the name and address here.',
    )

    class Meta:
        model = Event
        fields = [
            'title',
            'start_date', 'end_date',
            'opening_reception_date', 'opening_reception_time',
            'artist_talk_date', 'artist_talk_time',
            'closing_reception_date', 'closing_reception_time',
            'venue', 'location_name',
            'url', 'description', 'image',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'end_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'opening_reception_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'opening_reception_time': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
            'artist_talk_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'artist_talk_time': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
            'closing_reception_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'closing_reception_time': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
            'description': forms.Textarea(attrs={'rows': 5}),
        }
        labels = {
            'start_date': 'Opening / start date',
            'end_date': 'Closing / end date',
            'url': 'Event URL',
        }
        help_texts = {
            'end_date': 'For multi-day exhibitions. Leave blank for single-day events.',
            'image': 'Recommended: at least 800px wide, JPG or PNG.',
        }

    def __init__(self, *args, require_contact=False, **kwargs):
        super().__init__(*args, **kwargs)
        if require_contact:
            self.fields['submitter_name'].required = True
            self.fields['submitter_email'].required = True
        # DATE_INPUT_FORMATS must match the widget format
        for fname in ['start_date', 'end_date', 'opening_reception_date',
                      'artist_talk_date', 'closing_reception_date']:
            self.fields[fname].input_formats = ['%Y-%m-%d']
        for fname in ['opening_reception_time', 'artist_talk_time', 'closing_reception_time']:
            self.fields[fname].input_formats = ['%H:%M']

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('venue') and not cleaned.get('location_name'):
            raise forms.ValidationError(
                'Please select a venue from the directory or enter a custom location.'
            )
        end = cleaned.get('end_date')
        start = cleaned.get('start_date')
        if end and start and end < start:
            self.add_error('end_date', 'Closing date must be on or after the opening date.')
        return cleaned
