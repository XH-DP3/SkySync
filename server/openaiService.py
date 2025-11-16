import os
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

time = "The time of say is one of the following: Sunrise,Sunset,Morning,Afternoon,Evening,Night"
dancability = "Danceability is a measure of how suitable a song is for dancing, ranging from 0 to 1. A score of 0 means the song is not danceable at all, while a score of 1 indicates it is highly danceable. This score takes into account factors like tempo, rhythm, beat consistency, and energy, with higher scores indicating stronger, more rhythmically engaging tracks."
energy = "Energy in music refers to the intensity and liveliness of a track, with a range from 0 to 1. A score of 0 indicates a very calm, relaxed, or low-energy song, while a score of 1 represents a high-energy, intense track. It’s influenced by elements like tempo, loudness, and the overall drive or excitement in the music."
valence = "Valence in music measures the emotional tone or mood of a track, with a range from 0 to 1. A score of 0 indicates a song with a more negative, sad, or dark feeling, while a score of 1 represents a more positive, happy, or uplifting mood. Tracks with a high valence tend to feel joyful or energetic, while those with a low valence may evoke feelings of melancholy or sadness."
prompt = f"You are a helpful assistant that generates song parameters based on the weather data and the time of day. Generate a song parameters based on the weather data. the parameters are valence, energy, and dancability and are defined as float values from 0.00 to 1.00. Return the parameters in a JSON object with the keys 'valence', 'energy', and 'dancability'. the parameters are defined as follows: {dancability}, {energy}, {valence}. {time}"
weather = f"The weather data is "
load_dotenv()
client = OpenAI()

def getSongParams(weather_data):
    weather_prompt = f"{weather} {weather_data}"

    class AudioFeatures(BaseModel):
        valence: float
        danceability: float
        energy: float
        

    
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06", 
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": weather_prompt},
        ],
        response_format=AudioFeatures,
    )
    return completion.choices[0].message.parsed


def maketitle(song_params, weather_data):
    title_prompt = f"You are a helpful assistant that generates a title for a playlist based on the song parameters and the weather data. The song parameters are {song_params}. The weather data is {weather_data}. Generate a title for a song based on the song parameters and the weather data. The title should be a single word or phrase that captures the mood and energy of the song. The title should be 1-3 words long. parameters are valence, energy, and dancability and are defined as float values from 0.00 to 1.00. {dancability}, {energy}, {valence}"
    response = client.responses.create(
        model="gpt-5",
        input=title_prompt,
    )
    return response.output_text

def makedescription(song_params, weather_data):
    description = f"You are a helpful assistant that generates a title for a playlist based on the song parameters and the weather data. The song parameters are {song_params}. The weather data is {weather_data}. Generate a description for a playlist based on the song parameters and the weather data. The description should be a sentence that captures the mood and energy of the playlist. parameters are valence, energy, and dancability and are defined as float values from 0.00 to 1.00. {dancability}, {energy}, {valence}"
    response = client.responses.create(
        model="gpt-5",
        input=description,
    )
    return response.output_text




