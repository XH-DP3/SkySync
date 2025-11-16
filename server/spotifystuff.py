import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


client_id = '27464a703f5246d2a7357956cdea9d6e'
client_secret = 'e1813ceb7b004932812144a48182181c'

auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(auth_manager=auth_manager)

playlist_id = '7zsSWNoB46Ct4RHXv3M5vh'  # example Spotify playlist URI or ID

# Get playlist info (metadata)
# playlist = sp

playlist = sp.playlist(playlist_id)
print("Playlist Name:", playlist['name'])
print("Description:", playlist['description'])
print("Number of tracks:", playlist['tracks']['total'])

# Get tracks (Note: tracks are paginated, here is how to get first 100)
results = sp.playlist_tracks(playlist_id)
tracks = results['items']

query = "chill"  # mood keyword
results1 = sp.search(q=query, type='track', limit=20)


""" print("\nTracks in the playlist:")
for i, item in enumerate(tracks, start=1):
    track = item['track']
    print(f"{i}. {track['name']} - {track['artists'][0]['name']}")

print("\nTracks in the playlist:")
for i, item in enumerate(tracks, start=1):
    track = item['track']
    print(f"{i}. {track['name']} - {track['artists'][0]['name']}")   
 """


for idx, item in enumerate(results1['tracks']['items']):
    track = item
    print(f"{idx + 1}. {track['name']} by {track['artists'][0]['name']}")     

    
