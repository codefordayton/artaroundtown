from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand 
from apps.artists.management.commands._scrape_artists_csv import extract_artists 
from apps.artists.models import Artist, Piece
import requests
import os


class Command(BaseCommand):
    help = """Syncs a local Artists.csv file with a Digital Ocean space and
    relational database"""

    def add_arguments(self, parser):
        parser.add_argument("--csvfile", type=str, help="""Path to your artists
            csv file""")

    def handle(self, *args, **options):
        file_path = options['csvfile']

        with open(file_path, mode='r') as csv_file:
            artists = extract_artists(csv_file=csv_file)

        num_artists_processed = 1
        self.stdout.write(self.style.NOTICE("Uploading Images to Digital Ocean (this may take a while)...")) 

        for artist in artists:
            self.stdout.write(f"\rProcessing artist: ({num_artists_processed}/{len(artists)})... ", ending="")

            a = Artist(
                id=artist['id'], 
                name=artist['name'],
                slug=artist['slug'],
                bio=artist['bio'],
                primary_website=artist['primary_website'],
                secondary_website=artist['secondary_website'],
                email=artist['email'],
                phone=artist['phone'],
                artist_statement=artist['artist_statement'],
                facebook=artist['facebook'],
                instagram=artist['instagram'],
            )

            wix_profile_url = artist['profile_picture']
            _, ext = os.path.splitext(artist['profile_picture'])
            response = requests.get(wix_profile_url ,stream=True)

            if response.status_code == 200:
                a.profile_image.save(f"{a.slug}_profile{ext}", 
                                     ContentFile(response.content),
                                     save=False) 

            a.save()
            for piece in artist['pieces']:
                p = Piece(
                    slug=piece['slug'],
                    artist=a
                )
                wix_piece_url = piece['url']
                _, ext = os.path.splitext(wix_piece_url)
                response = requests.get(wix_piece_url, stream=True)
                if response.status_code == 200:
                    p.image.save(f"{p.slug}{ext}", 
                               ContentFile(response.content),
                               save=False)

                p.save()
            num_artists_processed += 1

        self.stdout.write(self.style.SUCCESS("\nSync complete!")) 
