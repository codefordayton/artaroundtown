"""Utilities to work with digital ocean object storage."""
import csv
import ast
import os
from dotenv import load_dotenv
import boto3
import requests
import uuid

load_dotenv()


def upload_artist_images(artist: dict):
    """This function uploads an artist's profile pic and art samples 
    to digital ocean object storage

    Object storage directory structure:

    <artist_uuid>/
    ├─ profile_picture.jpg/jpeg/png
    ├─ sample-pieces/
    │  ├─ <piece 1 slug>.jpg/jpeg/png
    │  ├─ <piece 2 slug>.jpg/jpeg/png
    │  ├─ ...
    │  ├─ <piece n slug>.jpg/jpeg/png
    """
    ACCESS_TOKEN = os.getenv('DIGITAL_OCEAN_PERSONAL_ACCESS_TOKEN')
    SECRET_KEY = os.getenv('DIGITAL_OCEAN_SECRET_KEY')
    BUCKET_BASE_PATH = os.getenv('BUCKET_BASE_PATH')
    BUCKET_NAME = os.getenv('BUCKET_NAME')

    s3_client = boto3.client('s3',
                            region_name='nyc3',
                            endpoint_url=BUCKET_BASE_PATH,
                            aws_access_key_id=ACCESS_TOKEN,
                            aws_secret_access_key=SECRET_KEY)

    
    # upload profile picture 
    profile_pic_url = artist['profile_picture']
    _, image_extension = os.path.splitext(artist['profile_picture'])
    profile_pic_object_key = f"media/artists/{artist['id']}/profile_picture{image_extension}"
    profile_img_response = requests.get(url=profile_pic_url, stream=True)
    
    s3_client.upload_fileobj(
        Fileobj=profile_img_response.raw,
        Bucket=BUCKET_NAME,
        Key=profile_pic_object_key
    )

    # upload sample pieces
    for piece in artist['pieces']:
        piece_object_key = f"media/artists/{artist['id']}/sample-pieces/{piece['slug']}"
        url = piece['url']
        piece_img_response = requests.get(url=url, stream=True)

        s3_client.upload_fileobj(
            Fileobj=piece_img_response.raw,
            Bucket=BUCKET_NAME,
            Key=piece_object_key
        )

def extract_artists(csv_file):
    NAME_IDX = 0 
    SLUG_IDX = 16
    BIO_IDX = 5
    MEDIUMS_IDX = 14
    PROFILE_PICTURE_IDX = 15
    PRIMARY_WEBSITE_IDX = 9
    SECONDARY_WEBSITE_IDX = 10 
    EMAIL_IDX = 2
    SAMPLE_PIECES_IDX = 11
    WIX_URI_PREFIX = "wix:image://v1/"
    WIX_BASE_URL = "https://static.wixstatic.com/media/"

    artists = []
    artist_reader = csv.reader(csv_file)
    next(artist_reader)

    for artist in artist_reader:
        # clean profile pic url 
        profile_picture_url = artist[PROFILE_PICTURE_IDX]
        if profile_picture_url.startswith(WIX_URI_PREFIX): 
            profile_picture_slug = profile_picture_url[len(WIX_URI_PREFIX):].split("/", 1)[0]
            profile_picture_url = WIX_BASE_URL + profile_picture_slug

        # clean sample_pieces to essential attributes
        sample_pieces = ast.literal_eval(artist[SAMPLE_PIECES_IDX])
        for idx, piece in enumerate(sample_pieces):
            piece_slug = piece['slug']
            piece_url = "https://static.wixstatic.com/media/" + piece_slug
            sample_pieces[idx] = {"slug": piece_slug, "url": piece_url}

        # clean slug
        slug = artist[SLUG_IDX][8:]
        slug_chars_to_remove = ".()"
        translation_tbl = str.maketrans("", "", slug_chars_to_remove)
        slug = slug.translate(translation_tbl)
        
        artist_object = {
            "id": str(uuid.uuid4()),
            "name": artist[NAME_IDX],
            "slug": slug, 
            "bio": artist[BIO_IDX],
            "mediums": artist[MEDIUMS_IDX],
            "profile_picture": profile_picture_url,
            "primary_website": artist[PRIMARY_WEBSITE_IDX],
            "secondary_website": artist[SECONDARY_WEBSITE_IDX],
            "email": artist[EMAIL_IDX],
            "pieces": sample_pieces,
        }
        artists.append(artist_object)
    
    return artists

if __name__ == "__main__":
    print("WARNING! This script may overwrite existing artist images.")
    user_confirmation = input("continue? [y/N] ")
    if user_confirmation.lower() == 'y': 
        artists = extract_artists(open("./Artists.csv")) 
        for a in artists:
            upload_artist_images(a)
    else:
        print("Cancelled")
