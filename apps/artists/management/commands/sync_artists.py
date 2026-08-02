from django.core.management.base import BaseCommand 
from apps.artists.management.commands._upload_digital_ocean import extract_artists, upload_artist_images
from apps.artists.models import Artist, Piece

class Command(BaseCommand):
    help = """Syncs a local Artists.csv file with a Digital Ocean space and
    relational database"""

    def add_arguments(self, parser):
        parser.add_argument("--csvfile", type=str, help="""Path to your artists
            csv file""")
        parser.add_argument(
            "-s", 
            "--skip-upload", 
            action="store_true", 
            help="""Skips uploading artist images to digital ocean. 
            Use if you just need load your table rows. 
            WARNING: This will overwrite the Digital ocean URL with WIX urls 
            for the profile pictures and artwork images"""
        )


    def handle(self, *args, **options):
        file_path = options['csvfile']
        skip_upload = options['skip_upload']
        csv_file = open(file_path, mode='r') 
        artists = extract_artists(csv_file=csv_file)

        num_artists_processed = 1
        self.stdout.write(self.style.NOTICE("Uploading Images to Digital Ocean (this may take a while)...")) # type: ignore[attr-defined]

        for artist in artists:
            self.stdout.write(f"\rProcessing artist: ({num_artists_processed}/{len(artists)})... ", ending="")

            if not skip_upload:
                upload_artist_images(artist) # object storage

            a = Artist(
                id=artist['id'], 
                name=artist['name'],
                slug=artist['slug'],
                bio=artist['bio'],
                profile_image=artist['profile_picture'],
                primary_website=artist['primary_website'],
                secondary_website=artist['secondary_website'],
                email=artist['email'],
                phone=artist['phone'],
                artist_statement=artist['artist_statement'],
                facebook=artist['facebook'],
                instagram=artist['instagram'],
            )
            a.save()
            for piece in artist['pieces']:
                p = Piece(
                    slug=piece['slug'],
                    url=piece['url'],
                    artist=a
                )
                p.save()
            num_artists_processed += 1

        csv_file.close()
        self.stdout.write(self.style.SUCCESS("\nSync complete!")) # type: ignore[attr-defined]
