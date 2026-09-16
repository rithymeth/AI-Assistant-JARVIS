import requests

from config.settings import WEATHER_LOCATION
from tools._geo import format_place_name, geocode

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SECONDS = 10

_WEATHER_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "depositing rime fog",
    51: "light drizzle", 53: "moderate drizzle", 55: "dense drizzle",
    56: "light freezing drizzle", 57: "dense freezing drizzle",
    61: "slight rain", 63: "moderate rain", 65: "heavy rain",
    66: "light freezing rain", 67: "heavy freezing rain",
    71: "slight snow fall", 73: "moderate snow fall", 75: "heavy snow fall",
    77: "snow grains",
    80: "slight rain showers", 81: "moderate rain showers", 82: "violent rain showers",
    85: "slight snow showers", 86: "heavy snow showers",
    95: "thunderstorm", 96: "thunderstorm with slight hail", 99: "thunderstorm with heavy hail",
}


def _describe_code(code: int) -> str:
    return _WEATHER_CODES.get(code, f"unknown conditions (code {code})")


def _require_forecast_fields(data: dict) -> tuple[dict, dict]:
    current = data.get("current") or {}
    daily = data.get("daily") or {}
    needed_current = (
        "weather_code",
        "temperature_2m",
        "apparent_temperature",
        "relative_humidity_2m",
        "wind_speed_10m",
    )
    needed_daily = ("temperature_2m_max", "temperature_2m_min", "precipitation_probability_max")
    if any(key not in current for key in needed_current) or any(key not in daily for key in needed_daily):
        raise RuntimeError("Weather service returned an incomplete forecast")
    if not daily["temperature_2m_max"] or not daily["temperature_2m_min"]:
        raise RuntimeError("Weather service returned an incomplete forecast")
    return current, daily


def get_weather(location: str | None = None) -> dict:
    location = (location or WEATHER_LOCATION or "").strip()
    if not location:
        raise ValueError(
            "No location given and no default WEATHER_LOCATION is set in .env — "
            "say which city, or set a default"
        )

    place = geocode(location)
    try:
        resp = requests.get(
            FORECAST_URL,
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max",
                "temperature_unit": "celsius",
                "wind_speed_unit": "kmh",
                "precipitation_unit": "mm",
                "timezone": "auto",
                "forecast_days": 1,
            },
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Weather lookup failed: {exc}") from exc
    current, daily = _require_forecast_fields(data)

    return {
        "location": format_place_name(place),
        "condition": _describe_code(current["weather_code"]),
        "temperature_c": current["temperature_2m"],
        "feels_like_c": current["apparent_temperature"],
        "humidity_percent": current["relative_humidity_2m"],
        "wind_kmh": current["wind_speed_10m"],
        "today_high_c": daily["temperature_2m_max"][0],
        "today_low_c": daily["temperature_2m_min"][0],
        "rain_chance_percent": daily["precipitation_probability_max"][0],
    }
