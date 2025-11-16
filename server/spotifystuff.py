import spotipy
from spotipy.oauth2 import SpotifyOAuth

from dotenv import load_dotenv
import os


load_dotenv()  # Load variables from .env into environment

client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')



auth_manager = SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri='http://127.0.0.1:8000/callback', scope="user-top-read playlist-read-private user-read-private")
sp = spotipy.Spotify(auth_manager=auth_manager)

playlist_id = '7zsSWNoB46Ct4RHXv3M5vh'  # example Spotify playlist URI or ID



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

    # Example: print track names and artists
    """for item in all_tracks:
        track = item['track']
        print(f"{track['name']} by {', '.join(artist['name'] for artist in track['artists'])}")"""

    # Assuming all_tracks is your full list of 700 track items

    #first_50_tracks = all_tracks[-50:]  # get first 50 items

    # Extract track IDs from first 50 tracks
    return [item['track']['id'] for item in all_tracks if item['track'] and item['track']['id']]

print(get_all_track_ids())




"""
# Get playlist info (metadata)
# playlist = sp

playlist = sp.current_user_top_tracks(limit=20, time_range='medium_term')
print("Playlist Name:", playlist['name'])
print("Description:", playlist['description'])
print("Number of tracks:", playlist['tracks']['total'])

# Get tracks (Note: tracks are paginated, here is how to get first 100)
results = sp.current_user_top_tracks(limit=50, time_range='medium_term')
tracks = results['items']

query = "chill"  # mood keyword
results1 = sp.search(q=query, type='track', limit=50)


 print("\nTracks in the playlist:")
for i, item in enumerate(tracks, start=1):
    track = item['track']
    print(f"{i}. {track['name']} - {track['artists'][0]['name']}")

print("\nTracks in the playlist:")
for i, item in enumerate(tracks, start=1):
    track = item['track']
    print(f"{i}. {track['name']} - {track['artists'][0]['name']}")   


for idx, item in enumerate(results['items']):
    track_name = item['name']
    artists = ", ".join(artist['name'] for artist in item['artists'])
    print(f"{idx + 1}. {track_name} by {artists}")

for idx, item in enumerate(results['tracks']['items']):
    track = item
    print(f"{idx + 1}. {track['name']} by {track['artists'][0]['name']}")   

"""
