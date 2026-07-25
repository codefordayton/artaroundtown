"""Stores images in digital ocean object storage.

This scripts assumes the existence of an Artists.csv
"""
import csv
import ast
import os
from botocore.client import Config
from dotenv import load_dotenv
import boto3

load_dotenv()


NAME_IDX = 0 
SAMPLE_PIECES_IDX = 11
PROFILE_PICTURE_IDX = 15
WIX_URI_PREFIX = "wix:image://v1/"
WIX_BASE_URL = "https://static.wixstatic.com/media/"
ACCESS_TOKEN = os.getenv('DIGITAL_OCEAN_PERSONAL_ACCESS_TOKEN')
SECRET_KEY = os.getenv('DIGITAL_OCEAN_SECRET_KEY')
BUCKET_BASE_PATH = "https://nyc3.digitaloceanspaces.com"

print(SECRET_KEY)
print(ACCESS_TOKEN)

session = boto3.Session()
s3_client = session.client('s3',
                        region_name='nyc3',
                        endpoint_url=BUCKET_BASE_PATH,
                        aws_access_key_id=ACCESS_TOKEN,
                        aws_secret_access_key=SECRET_KEY)

objects = s3_client.list_objects_v2(
    Bucket='artaroundtown'
)

with open('Artists.csv') as csvfile:
    artist_reader = csv.reader(csvfile)
    next(artist_reader)

    for artist in artist_reader:
        name = artist[NAME_IDX]
        sample_pieces = ast.literal_eval(artist[SAMPLE_PIECES_IDX])
        profile_picture_url = artist[PROFILE_PICTURE_IDX]


        if profile_picture_url.startswith(WIX_URI_PREFIX): 
            profile_picture_slug = profile_picture_url[len(WIX_URI_PREFIX):].split("/", 1)[0]
            profile_picture_url = WIX_BASE_URL + profile_picture_slug

        for piece in sample_pieces:
            piece_slug = piece['slug']
            piece_url = "https://static.wixstatic.com/media/" + piece_slug
        
        checking = f"""Artist name: {name}
        Pieces: {sample_pieces}
        Profile pic url: {profile_picture_url}
        """
        print(checking)
