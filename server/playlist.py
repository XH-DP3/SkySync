import spotipy
from spotipy.oauth2 import SpotifyOAuth

from dotenv import load_dotenv
import os

from reccobeats_util import filter_tracks_by_audio_ft
from openaiService import getSongParams, maketitle
from weather import get_weather_state

import random

load_dotenv()  # Load variables from .env into environment

client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')



auth_manager = SpotifyOAuth(client_id=client_id, 
                            client_secret=client_secret, 
                            redirect_uri='http://127.0.0.1:8000/callback', 
                            scope="user-top-read playlist-read-private user-read-private playlist-modify-public playlist-modify-private",
                            cache_path="token_playback.cache")


sp = spotipy.Spotify(auth_manager=auth_manager)



def make_new_playlist(weather_state):
    song_params = getSongParams(weather_state)
    user = sp.current_user()
    new_playlist = sp.user_playlist_create(user['id'], maketitle(song_params, weather_state), public=False)
    new_playlist_id = new_playlist["id"]
    random.shuffle(filter_tracks_by_audio_ft(song_params))
    filtered_track_ids = filter_tracks_by_audio_ft(song_params)[:50]
    track_URIs = [f"spotify:track:{tid["ori_id"]}" for tid in filtered_track_ids]
    print(track_URIs)
    sp.playlist_add_items(new_playlist_id, track_URIs)



make_new_playlist(get_weather_state())
#make_new_playlist({'current_weather': 'Clear sky', 'current_time': 'Morning'})

