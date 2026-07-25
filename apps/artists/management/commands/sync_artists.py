from django.core.management.base import BaseCommand 
from apps.artists.management.commands._upload_digital_ocean import extract_artist_images, upload_artist_images

class Command(BaseCommand):
    help = """Syncs a local Artists.csv file with a Digital Ocean space and
    relational database"""

    def add_arguments(self, parser):
        parser.add_argument("--csvfile", type=str, help="""Path to your artists
            csv file""")

    def handle(self, *args, **options):
        file_path = options['csvfile']
        csv_file = open(file_path, mode='r') 

        artists = extract_artist_images(csv_file=csv_file)
        for artist in artists:
            upload_artist_images(artist)

        csv_file.close()
        self.stdout.write(self.style.SUCCESS("Sync successful!")) # type: ignore[attr-defined]


