import requests
import pandas as pd
from spotifystuff import get_all_track_ids
from openaiService import getSongParams
from weather import get_weather_state

url = "https://api.reccobeats.com/v1/audio-features"

# List of track IDs (Spotify or ReccoBeats IDs), between 1 and 40
track_ids = get_all_track_ids()

def chunk_list(lst, chunk_size):
    """Yield successive chunks from lst of size chunk_size."""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

all_filtered_features = []

track_ids = get_all_track_ids()  # Your 700+ track IDs

for chunk in chunk_list(track_ids, 40):
    params = {
        'ids': ','.join(chunk)
    }
    headers = {
        'Accept': 'application/json'
    }
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    
    for track in data['content']:
        filtered = {
            'id': track.get('id'),
            'valence': track.get('valence'),
            'danceability': track.get('danceability'),
            'energy': track.get('energy')
        }
        all_filtered_features.append(filtered)

# all_filtered_features now contains filtered data for all tracks

filtered_high_valence = [track for track in all_filtered_features if track['valence'] > 0.7]

def in_range_float(min, max, val):
    return min <= val and val <= max

def filter_tracks(vals):
    valence = vals.valence
    danceability = vals.danceability
    energy = vals.energy

    print(f"Valence: {valence}")

    return [track for track in all_filtered_features if (in_range_float(valence-0.1, valence+0.1, track['valence']) and in_range_float(danceability-0.2, danceability+0.2, track['danceability']) and in_range_float(energy-0.3, energy+0.3, track['energy']))]

df_ff = pd.DataFrame(all_filtered_features)

song_params = getSongParams(get_weather_state())
print(song_params)
filtered_high_valence = filter_tracks(song_params)
df_fhv = pd.DataFrame(filtered_high_valence)

print("Features (All)")
print(df_ff)

print(">0.7 Valence")
print(df_fhv)
#print(response.text) 


"""
params = {
    'ids': ','.join(track_ids)
}

headers = {
  'Accept': 'application/json'
}

response = requests.request("GET", url, headers=headers, params=params)

data = response.json()
filtered_features = []
for track in data['content']:
    filtered = {
        'id': track.get('id'),
        'valence': track.get('valence'),
        'danceability': track.get('danceability'),
        'energy': track.get('energy')
    }
    filtered_features.append(filtered)

filtered_high_valence = [track for track in filtered_features if track['valence'] > 0.7]

df_ff = pd.DataFrame(filtered_features)

df_fhv = pd.DataFrame(filtered_high_valence)

print("Features (All)")
print(df_ff)

print(">0.7 Valence")
print(df_fhv)
#print(response.text) """