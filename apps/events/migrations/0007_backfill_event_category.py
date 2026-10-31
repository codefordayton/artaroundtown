from django.db import migrations


def backfill(apps, schema_editor):
    """Every listing imported before the category field reached the submit
    form was a gallery show, so label the uncategorized ones Visual Arts."""
    Event = apps.get_model('events', 'Event')
    Event.objects.filter(category='').update(category='visual_arts')


class Migration(migrations.Migration):
    dependencies = [
        ('events', '0006_event_category_choices'),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
