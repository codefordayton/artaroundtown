"""Utilities to work with digital ocean object storage."""
import csv
import ast
import uuid

def extract_artists(csv_file):
    """This function takes in a python File object and exports 
    a list of artist objects (dicts). It assumes csv_file 
    is the official artfordayton's Artists.csv extracted from wix
    """
    NAME_IDX = 0 
    SLUG_IDX = 16
    BIO_IDX = 5
    MEDIUMS_IDX = 14
    PROFILE_PICTURE_IDX = 15
    PRIMARY_WEBSITE_IDX = 9
    SECONDARY_WEBSITE_IDX = 10 
    EMAIL_IDX = 2
    PHONENUM_IDX = 4
    ARTIST_STATEMENT_IDX = 6
    FACEBOOK_IDX = 7
    INSTAGRAM_IDX = 8
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
            "phone": artist[PHONENUM_IDX],
            "artist_statement": artist[ARTIST_STATEMENT_IDX],
            "facebook": artist[FACEBOOK_IDX],
            "instagram": artist[INSTAGRAM_IDX],
            "pieces": sample_pieces,
        }
        artists.append(artist_object)
    
    return artists

if __name__ == "__main__":
    "Used for debugging artists object"
    artists = extract_artists(open("./Artists.csv")) 
    print("Artists:\n")
    for a in artists:
        print(f"{a}\n")
