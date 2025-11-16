import spotipy
from spotipy.oauth2 import SpotifyOAuth

from dotenv import load_dotenv
import os


load_dotenv()  # Load variables from .env into environment

client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')



auth_manager = SpotifyOAuth(client_id=client_id, 
                            client_secret=client_secret, 
                            redirect_uri='http://127.0.0.1:8000/callback', 
                            scope="user-top-read playlist-read-private user-read-private playlist-modify-public playlist-modify-private user-modify-playback-state user-read-playback-state",
                            cache_path=".cache")
sp = spotipy.Spotify(auth_manager=auth_manager)

playlist_id = '0JiVp7Z0pYKI8diUV6HJyQ'  # example Spotify playlist URI or ID



def get_all_track_ids():
    all_tracks = []
    limit = 100  # max allowed by Spotify API
    offset = 0

    while True:
        response = sp.playlist_items(playlist_id, limit=limit, offset=offset)
        tracks = response['items']
        all_tracks.extend(tracks)
        
        if len(tracks) < limit:
            # Fetched all tracks
            break
        offset += limit

    print(f"Total tracks fetched: {len(all_tracks)}")


    # Assuming all_tracks is your full list of 700 track items

    # Extract track IDs from first 50 tracks
    return [item['track']['id'] for item in all_tracks if item['track'] and item['track']['id']]



