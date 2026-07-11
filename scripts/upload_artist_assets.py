"""Stores images in digital ocean object storage.

This scripts assumes the existence of an Artists.csv
"""
import csv
import ast
import os
#import requests

NAME_IDX = 0 
SAMPLE_PIECES_IDX = 11
PROFILE_PICTURE_IDX = 15
WIX_URI_PREFIX = "wix:image://v1/"
WIX_BASE_URL = "https://static.wixstatic.com/media/"
DIGITAL_OCEAN_TOKEN = os.getenv('DIGITAL_OCEAN_PERSONAL_ACCESS_TOKEN')
print(DIGITAL_OCEAN_TOKEN)

with open('Artists.csv') as csvfile:
    artist_reader = csv.reader(csvfile)
    next(artist_reader)

    for artist in artist_reader:
        name = artist[NAME_IDX]
        sample_pieces = ast.literal_eval(artist[SAMPLE_PIECES_IDX])
        profile_picture_url = artist[PROFILE_PICTURE_IDX]

        
        BUCKET_BASE_PATH = 

        if profile_picture_url.startswith(WIX_URI_PREFIX): 
            profile_picture_slug = profile_picture_url[len(WIX_URI_PREFIX):].split("/", 1)[0]
            profile_picture_url = WIX_BASE_URL + profile_picture_slug

        for piece in sample_pieces:
            piece_slug = piece['slug']
            piece_url = "https://static.wixstatic.com/media/" + piece_slug
