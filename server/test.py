from openaiService import getSongParams

from weather import get_weather_state

weather_data = get_weather_state()
print(weather_data)

song_params = getSongParams(weather_data)
print(f"Valence: {song_params.valence}")         # Output: 0.85 (example)
print(f"Danceability: {song_params.danceability}") # Output: 0.72 (example)
print(f"Energy: {song_params.energy}")