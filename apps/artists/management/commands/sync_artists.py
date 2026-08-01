from django.core.management.base import BaseCommand 
from apps.artists.management.commands._upload_digital_ocean import extract_artists, upload_artist_images
from apps.artists.models import Artist, Piece

class Command(BaseCommand):
    help = """Syncs a local Artists.csv file with a Digital Ocean space and
    relational database"""

    def add_arguments(self, parser):
        parser.add_argument("--csvfile", type=str, help="""Path to your artists
            csv file""")

    def handle(self, *args, **options):
        file_path = options['csvfile']
        csv_file = open(file_path, mode='r') 
        artists = extract_artists(csv_file=csv_file)

        a = Artist(artists[0])
        for artist in artists:
            # upload to s3
            #upload_artist_images(artist)
                
            # upload artist to database
            a = Artist(
                id=artist['id'], 
                name=artist['name'],
                slug=artist['slug'],
                bio=artist['bio'],
                profile_image=artist['profile_picture'],
                primary_website=artist['primary_website'],
                secondary_website=artist['secondary_website'],
                email=artist['email']
            )      
            a.save()
            
            for piece in artist['pieces']:
                p = Piece(
                    slug=piece['slug'],
                    url=piece['url'],
                    artist=a
                )
                p.save()


        csv_file.close()
        self.stdout.write(self.style.SUCCESS("Sync successful!")) # type: ignore[attr-defined]


