import os
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

 


def getSongParams(weather_data):
    load_dotenv()
    client = OpenAI()
    time = "The time of say is one of the following: Sunrise,Sunset,Morning,Afternoon,Evening,Night"
    dancability = "Danceability is a measure of how suitable a song is for dancing, ranging from 0 to 1. A score of 0 means the song is not danceable at all, while a score of 1 indicates it is highly danceable. This score takes into account factors like tempo, rhythm, beat consistency, and energy, with higher scores indicating stronger, more rhythmically engaging tracks."
    energy = "Energy in music refers to the intensity and liveliness of a track, with a range from 0 to 1. A score of 0 indicates a very calm, relaxed, or low-energy song, while a score of 1 represents a high-energy, intense track. It’s influenced by elements like tempo, loudness, and the overall drive or excitement in the music."
    valence = "Valence in music measures the emotional tone or mood of a track, with a range from 0 to 1. A score of 0 indicates a song with a more negative, sad, or dark feeling, while a score of 1 represents a more positive, happy, or uplifting mood. Tracks with a high valence tend to feel joyful or energetic, while those with a low valence may evoke feelings of melancholy or sadness."
    prompt = f"You are a helpful assistant that generates song parameters based on the weather data and the time of day. Generate a song parameters based on the weather data. the parameters are valence, energy, and dancability and are defined as float values from 0.00 to 1.00. Return the parameters in a JSON object with the keys 'valence', 'energy', and 'dancability'. the parameters are defined as follows: {dancability}, {energy}, {valence}. {time}"
    weather_prompt = f"The weather data is {weather_data}."

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



