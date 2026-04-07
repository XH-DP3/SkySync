import clearDay from "../assets/clear_day.png";
import clearNight from "../assets/clear_night.png";
import fog from "../assets/fog.png";
import mainBackground from "../assets/main_background.png";
import overcastDay from "../assets/overcast_day.png";
import overcastNight from "../assets/overcast_night.png";
import partlyCloudyDay from "../assets/partly_cloudy_day.png";
import partlyCloudyNight from "../assets/partly_cloudy_night.png";
import rainDay from "../assets/rain_day.gif";
import rainNight from "../assets/rain_night.gif";
import snowDay from "../assets/snow_day.gif";
import snowNight from "../assets/snow_night.gif";
import thunderDay from "../assets/thunder_day.gif";
import thunderNight from "../assets/thunder_night.gif";

export const MAIN_BACKGROUND = mainBackground;

const WEATHER_IMAGES = {
  clear: { day: clearDay, night: clearNight },
  "partly cloudy": { day: partlyCloudyDay, night: partlyCloudyNight },
  "mainly clear": { day: partlyCloudyDay, night: partlyCloudyNight },
  overcast: { day: overcastDay, night: overcastNight },
  fog: { day: fog, night: fog },
  rain: { day: rainDay, night: rainNight },
  snow: { day: snowDay, night: snowNight },
  thunderstorm: { day: thunderDay, night: thunderNight }
};

function normalizeDayFlag(isDay) {
  if (isDay === true || isDay === 1 || isDay === "1") {
    return true;
  }
  if (isDay === false || isDay === 0 || isDay === "0") {
    return false;
  }
  return Boolean(isDay);
}

export function getWeatherBackground(category, isDay) {
  const normalizedCategory = String(category || "").trim().toLowerCase();
  const timeOfDay = normalizeDayFlag(isDay) ? "day" : "night";
  return WEATHER_IMAGES[normalizedCategory]?.[timeOfDay] ?? MAIN_BACKGROUND;
}
