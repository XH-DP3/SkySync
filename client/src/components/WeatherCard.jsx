import PropTypes from "prop-types";

function WeatherRow({ label, value }) {
  return (
    <p className="weather-row">
      <span className="weather-label">{label}:</span> {value}
    </p>
  );
}

export default function WeatherCard({ weather }) {
  const locationBits = [
    weather.location?.name,
    weather.location?.admin1,
    weather.location?.country
  ].filter(Boolean);

  const forecastLabelMap = {
    now: "Now",
    tonight: "Tonight",
    tomorrow_morning: "Tomorrow Morning"
  };

  return (
    <div className="weather-bubble">
      <h1 className="bubble-title">Current Weather</h1>
      {locationBits.length > 0 && (
        <WeatherRow label="📍 Location" value={locationBits.join(", ")} />
      )}
      <WeatherRow
        label="🧭 Forecast Mode"
        value={forecastLabelMap[weather.forecast_mode] ?? "Now"}
      />
      <WeatherRow label="📅 Date" value={weather.date} />
      <WeatherRow label="🕒 Time" value={weather.time} />
      <WeatherRow label="🌡 Temperature" value={`${weather.temperature} °C`} />
      <WeatherRow label="⛅ Condition" value={weather.condition} />
      <WeatherRow label="🕶 Mood Window" value={weather.time_of_day ?? "Unknown"} />
      <WeatherRow label="🌅 Sunrise" value={weather.sunrise} />
      <WeatherRow label="🌇 Sunset" value={weather.sunset} />
    </div>
  );
}

WeatherRow.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired
};

WeatherCard.propTypes = {
  weather: PropTypes.shape({
    date: PropTypes.string.isRequired,
    time: PropTypes.string.isRequired,
    temperature: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    condition: PropTypes.string.isRequired,
    forecast_mode: PropTypes.string,
    time_of_day: PropTypes.string,
    sunrise: PropTypes.string.isRequired,
    sunset: PropTypes.string.isRequired,
    location: PropTypes.shape({
      name: PropTypes.string,
      admin1: PropTypes.string,
      country: PropTypes.string
    })
  }).isRequired
};
