import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

load_dotenv()

_client: spotipy.Spotify | None = None


def get_spotify_client() -> spotipy.Spotify:
    global _client
    if _client is None:
        auth_manager = SpotifyClientCredentials(
            client_id=os.environ["SPOTIFY_CLIENT_ID"],
            client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        )
        _client = spotipy.Spotify(auth_manager=auth_manager)
    return _client
