import os
os.system("pip install plotly")  # Ensure plotly is installed before import

import math
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

import numpy as np
import pandas as pd
import requests
import streamlit as st
import pytz
import plotly.express as px

st.set_page_config(page_title="ZainWeatherApp", page_icon="🌦️", layout="wide")


# Add styling for metrics and weather description
st.markdown("""
<style>
.stMetric {
    border: 1px solid #e5e7eb;
    border-radius: 0 !important;
    padding: 1rem !important;
    background: white;
}
.stMetric-value {
    font-size: 1.5rem !important;
    font-weight: 600 !important;
}
.stMetric-label {
    font-size: 0.9rem !important;
    color: #6b7280 !important;
}
.weather-desc {
    background: #e0e7ff;
    color: #2563eb;
    padding: 0.4rem 1rem;
    border-radius: 999px;
    display: inline-block;
    font-weight: 600;
    margin: 0.5rem 0;
}
.temp-display {
    font-size: 2.5rem;
    font-weight: 600;
    margin: 0.5rem 0;
}

/* Card container used for small panels */
.panel {
  background: #ffffff;
  border: 1px solid #e6e7eb;
  padding: 0.8rem;
  border-radius: 6px;
  box-shadow: 0 1px 2px rgba(16,24,40,0.03);
}

/* Make Streamlit metrics use subtle square corners and consistent sizing */
div[data-testid="stMetric"] {
  border-radius: 4px !important;
  padding: 0.45rem 0.6rem !important;
  background: #ffffff !important;
  border: 1px solid #e6e7eb !important;
  box-shadow: none !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 0.6rem !important;
}

/* Label on the left, value on the right */
div[data-testid="stMetricLabel"] {
  font-size: 0.95rem !important;
  color: #6b7280 !important;
  text-align: left !important;
  flex: 1 1 auto !important;
  margin-right: 0.6rem !important;
}

div[data-testid="stMetricValue"] {
  font-size: 1.3rem !important;
  font-weight: 700 !important;
  color: #0f172a !important;
  text-align: right !important;
  min-width: 4.5ch !important;
}

/* Ensure metrics inside small right column stack nicely */
.panel > div[data-testid="stMetric"] {
  margin-bottom: 0.5rem !important;
}

/* Row helper when showing multiple metrics directly under a panel */
.panel .metric-row { display:flex; gap:0.6rem; margin-top:0.6rem; }
.panel .metric-row > div { flex:1; }

/* Prominent temperature display (no pill) */
.temp-large { font-size: 3rem; font-weight: 800; color: #0f172a; }

/* Small badge for weather description (subtle, not full pill for all items) */
.weather-badge { display:inline-block; background:#eef2ff; color:#3730a3; padding:0.28rem 0.6rem; border-radius:6px; font-weight:600; margin-top:0.5rem; }

/* Dark mode adjustments */
[data-theme="dark"] .panel {
  background: #071122;
  border-color: #203040;
}
[data-theme="dark"] div[data-testid="stMetric"] {
  background: #08131b !important;
  border-color: #1f2a34 !important;
}
[data-theme="dark"] div[data-testid="stMetricValue"] {
  color: #e6eef8 !important;
}
[data-theme="dark"] div[data-testid="stMetricLabel"] {
  color: #93a0b8 !important;
}
[data-theme="dark"] .weather-badge { background:#0f1724; color:#bfdbfe; }

@media (max-width: 640px) {
  div[data-testid="stMetric"] {
    flex-direction: column !important;
    align-items: flex-start !important;
  }
  div[data-testid="stMetricValue"] { text-align: left !important; }
  .temp-large { font-size: 2.2rem; }
}
</style>
""", unsafe_allow_html=True)

# Place title and small branding in the sidebar so the main dashboard starts at the top
with st.sidebar:
    st.markdown("<div style='display:flex;align-items:center;gap:0.6rem'>🌦️ <strong style='font-size:1.1rem'>ZainWeather</strong></div>", unsafe_allow_html=True)
    st.caption("Powered by Open‑Meteo — no API keys required")


# Weather code to icon/description mapping
WMO_CODES = {
    0: ("☀️", "Clear sky"),
    1: ("🌤️", "Mainly clear"),
    2: ("⛅", "Partly cloudy"),
    3: ("☁️", "Overcast"),
    45: ("🌫️", "Foggy"),
    48: ("🌫️", "Depositing rime fog"),
    51: ("🌦️", "Light drizzle"),
    53: ("🌦️", "Moderate drizzle"),
    55: ("🌧️", "Dense drizzle"),
    56: ("🌧️", "Light freezing drizzle"),
    57: ("🌧️", "Dense freezing drizzle"),
    61: ("🌧️", "Slight rain"),
    63: ("🌧️", "Moderate rain"),
    65: ("🌧️", "Heavy rain"),
    66: ("🌧️", "Light freezing rain"),
    67: ("🌧️", "Heavy freezing rain"),
    71: ("🌨️", "Slight snow"),
    73: ("🌨️", "Moderate snow"),
    75: ("🌨️", "Heavy snow"),
    77: ("❄️", "Snow grains"),
    80: ("🌦️", "Slight rain showers"),
    81: ("🌧️", "Moderate rain showers"),
    82: ("🌧️", "Violent rain showers"),
    85: ("🌨️", "Slight snow showers"),
    86: ("🌨️", "Heavy snow showers"),
    95: ("⛈️", "Thunderstorm"),
    96: ("⛈️", "Thunderstorm with slight hail"),
    99: ("⛈️", "Thunderstorm with heavy hail"),
}

def get_weather_icon(code: int) -> tuple:
    """Get weather icon and description for a WMO code."""
    return WMO_CODES.get(code, ("❓", "Unknown"))

def temp_color(temp: float) -> str:
    """Return color based on temperature."""
    if temp < 0: return "#A4CAFE"  # Very cold - light blue
    elif temp < 10: return "#60A5FA"  # Cold - blue
    elif temp < 20: return "#34D399"  # Mild - green
    elif temp < 30: return "#FBBF24"  # Warm - yellow
    else: return "#F87171"  # Hot - red

# -----------------------------
# Utilities & Caching
# -----------------------------
@st.cache_data(show_spinner=False, ttl=60 * 30)
def geocode_place(q: str, count: int = 5) -> pd.DataFrame:
    """Search locations using Open-Meteo Geocoding API."""
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": q, "count": count, "language": "en", "format": "json"}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    if not data or "results" not in data:
        return pd.DataFrame()
    rows = []
    for it in data["results"]:
        rows.append({
            "name": it.get("name"),
            "country": it.get("country"),
            "admin1": it.get("admin1"),
            "lat": it.get("latitude"),
            "lon": it.get("longitude"),
            "timezone": it.get("timezone"),
            "elevation": it.get("elevation"),
        })
    return pd.DataFrame(rows)

@st.cache_data(show_spinner=False, ttl=5 * 60)
def fetch_forecast(lat: float, lon: float, tz: str) -> Dict[str, Any]:
    """Fetch current, hourly, and daily weather from Open-Meteo."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "precipitation",
            "rain",
            "snowfall",
            "precipitation_probability",
            "weathercode",  # Added weathercode to hourly
            "cloud_cover",
            "windspeed_10m",
            "windgusts_10m",
            "winddirection_10m",
            "uv_index",
            "uv_index_clear_sky",
        ]),
        "daily": ",".join([
            "weathercode",
            "temperature_2m_max",
            "temperature_2m_min",
            "temperature_2m_max",
            "temperature_2m_min",
            "windspeed_10m_max",
        ]),
        "current_weather": True,
        "timezone": tz,
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

@st.cache_data(show_spinner=False, ttl=10 * 60)
def fetch_air_quality(lat: float, lon: float, tz: str) -> Dict[str, Any]:
    """Fetch hourly air quality (PM2.5, PM10, O3, NO2, SO2) from Open-Meteo AQ API."""
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join([
            "pm2_5",
            "pm10",
            "ozone",
            "nitrogen_dioxide",
            "sulphur_dioxide",
            "carbon_monoxide",
            "us_aqi",
        ]),
        "timezone": tz,
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

# -----------------------------
# Helpers: AQI computation (fallback if us_aqi absent)
# -----------------------------
# Breakpoints for US EPA AQI (2012 PM2.5, PM10; 2015 O3 8hr; NO2 1hr; SO2 1hr simplified)
# This is a simplified implementation for demo purposes.
AQI_BP = {
    "pm2_5": [
        (0.0, 12.0, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 350.4, 301, 400),
        (350.5, 500.4, 401, 500),
    ],
    "pm10": [
        (0, 54, 0, 50), (55, 154, 51, 100), (155, 254, 101, 150),
        (255, 354, 151, 200), (355, 424, 201, 300), (425, 504, 301, 400), (505, 604, 401, 500)
    ],
}

AQI_CATEGORIES = [
    (0, 50, "Good", "Air quality is satisfactory."),
    (51, 100, "Moderate", "Unusually sensitive people should limit outdoor exertion."),
    (101, 150, "Unhealthy for Sensitive Groups", "Reduce prolonged or heavy exertion."),
    (151, 200, "Unhealthy", "Avoid prolonged or heavy exertion; sensitive groups should stay indoors."),
    (201, 300, "Very Unhealthy", "Health alert: everyone may experience serious effects."),
    (301, 500, "Hazardous", "Health warnings of emergency conditions."),
]

def calc_aqi_subindex(pollutant: str, conc: float) -> Optional[float]:
    bps = AQI_BP.get(pollutant)
    if not bps or conc is None or math.isnan(conc):
        return None
    for c_low, c_high, aqi_low, aqi_high in bps:
        if c_low <= conc <= c_high:
            return (aqi_high - aqi_low) / (c_high - c_low) * (conc - c_low) + aqi_low
    return None


def categorize_aqi(aqi: float) -> str:
    for lo, hi, name, _ in AQI_CATEGORIES:
        if lo <= aqi <= hi:
            return name
    return "Unknown"


def aqi_advice(aqi: float) -> str:
    for lo, hi, name, advice in AQI_CATEGORIES:
        if lo <= aqi <= hi:
            return advice
    return "—"

# -----------------------------
# UX: Sidebar controls
# -----------------------------
with st.sidebar:
    st.subheader("🔎 Location & Settings")
    q = st.text_input("Search a place", value="Karachi")
    if q:
        results = geocode_place(q)
        if results.empty:
            st.warning("No locations found. Try a different name.")
            st.stop()
        choice = st.selectbox(
            "Select a location",
            options=list(results.index),
            format_func=lambda i: f"{results.loc[i, 'name']}, {results.loc[i, 'admin1'] or ''} {results.loc[i, 'country'] or ''}"
        )
        sel = results.loc[choice]
        lat, lon = float(sel.lat), float(sel.lon)
        tz = sel.timezone or "UTC"
        # Make the map smaller using st.container and height argument
        with st.container():
            st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}), use_container_width=True, height=180)

    st.markdown("<hr style='margin:1rem 0 0.5rem 0;border:0;border-top:1px solid #e5e7eb;'>", unsafe_allow_html=True)
    st.subheader("🎒 Wardrobe & Health")
    user_pref = st.multiselect(
        "Preferences",
        ["Hate rain", "Sensitive to cold", "Allergy-prone", "Runner", "Cyclist", "Carry laptop"],
    )
    st.divider()
    units = st.radio("Units", ["Metric (°C, m/s)", "Imperial (°F, mph)"])
    show_hourly = st.checkbox("Show hourly charts", value=True)
    show_daily = st.checkbox("Show 7‑day outlook", value=True)
    show_air = st.checkbox("Show air quality panel", value=True)

    

# -----------------------------
# Fetch data
# -----------------------------
with st.spinner("Fetching forecast…"):
    fc = fetch_forecast(lat, lon, tz)
    aq = fetch_air_quality(lat, lon, tz) if show_air else None

# -----------------------------
# Parse & present current conditions
# -----------------------------
current = fc.get("current_weather", {})
hourly = fc.get("hourly", {})
daily = fc.get("daily", {})

# Enhanced current weather display with city name and icons
city_display = f"{sel['name']}"
if sel.get('admin1'):
    city_display += f", {sel['admin1']}"
if sel.get('country'):
    city_display += f", {sel['country']}"
# Reduce margin above and below city name
st.markdown(f"<div style='font-size:1.35rem;font-weight:700;margin-bottom:0.2em;margin-top:0.2em'>{city_display}</div>", unsafe_allow_html=True)

code = current.get('weathercode', 0)
icon, description = get_weather_icon(code)
temp = current.get('temperature', '—')
temp_str = f"{temp}°C" if units.startswith("Metric") else f"{temp * 9/5 + 32:.1f}°F"
wind_speed = current.get('windspeed', '—')
wind_str = f"{wind_speed} km/h" if units.startswith("Metric") else f"{wind_speed * 0.621371:.1f} mph"

# Modern minimal CSS for cards and metrics (no gradients, no full-body backgrounds)
st.markdown("""
<style>
/* Card container used for small panels */
.panel {
  background: #ffffff;
  border: 1px solid #e6e7eb;
  padding: 0.8rem;
  border-radius: 6px;
  box-shadow: 0 1px 2px rgba(16,24,40,0.03);
}

/* Make Streamlit metrics use subtle square corners and consistent sizing */
div[data-testid="stMetric"] {
  border-radius: 4px !important;
  padding: 0.45rem 0.6rem !important;
  background: #ffffff !important;
  border: 1px solid #e6e7eb !important;
  box-shadow: none !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 0.6rem !important;
  color: #0f172a !important;
}

/* Label on the left, value on the right */
div[data-testid="stMetricLabel"] {
  font-size: 0.95rem !important;
  color: #6b7280 !important;
  text-align: left !important;
  flex: 1 1 auto !important;
  margin-right: 0.6rem !important;
}

div[data-testid="stMetricValue"] {
  font-size: 1.3rem !important;
  font-weight: 700 !important;
  color: #0f172a !important;
  text-align: right !important;
  min-width: 4.5ch !important;
}

/* Ensure metrics inside small right column stack nicely */
.panel > div[data-testid="stMetric"] {
  margin-bottom: 0.5rem !important;
}

/* Row helper when showing multiple metrics directly under a panel */
.panel .metric-row { display:flex; gap:0.6rem; margin-top:0.6rem; }
.panel .metric-row > div { flex:1; }

/* Prominent temperature display (no pill) */
.temp-large { font-size: 3rem; font-weight: 800; color: #0f172a; }

/* Small badge for weather description (subtle, not full pill for all items) */
.weather-badge { display:inline-block; background:#eef2ff; color:#3730a3; padding:0.28rem 0.6rem; border-radius:6px; font-weight:600; margin-top:0.5rem; }

/* Dark mode adjustments */
[data-theme="dark"] .panel {
  background: #071122 !important;
  border-color: #203040 !important;
}
[data-theme="dark"] div[data-testid="stMetric"] {
  background: #08131b !important;
  border-color: #1f2a34 !important;
  color: #e6eef8 !important;
}
[data-theme="dark"] div[data-testid="stMetricValue"] {
  color: #e6eef8 !important;
}
[data-theme="dark"] div[data-testid="stMetricLabel"] {
  color: #93a0b8 !important;
}
[data-theme="dark"] .weather-badge { background:#0f1724 !important; color:#bfdbfe !important; }
[data-theme="dark"] .temp-large { color: #e6eef8 !important; }

@media (max-width: 640px) {
  div[data-testid="stMetric"] {
    flex-direction: column !important;
    align-items: flex-start !important;
  }
  div[data-testid="stMetricValue"] { text-align: left !important; }
  .temp-large { font-size: 2.2rem; }
}
</style>
""", unsafe_allow_html=True)

# Layout: left shows temp & description, metrics moved below it; right kept for future small widgets
with st.container():
    # Use a single column to make the panel and metrics fit the body width with margins
    st.markdown(
        """
        <div style="max-width: 90rem; margin: 1.5rem auto 1.2rem auto;">
            <div class="panel" style="margin-bottom:1.2rem;">
              <div style="display:flex;align-items:center;gap:1rem">
                <div style="font-size:3.8rem">{icon}</div>
                <div>
                  <div class="temp-large">{temp_str}</div>
                  <div class="weather-badge">{description}</div>
                </div>
              </div>
              <!-- metrics row placed under the temperature display -->
              <div style="margin-top:0.75rem"></div>
            </div>
        """.format(icon=icon, temp_str=temp_str, description=description),
        unsafe_allow_html=True
    )

    # Metrics displayed as a row under the temperature panel, also centered and max-width
    mcols = st.columns(3)
    with mcols[0]:
        st.metric("💨 Wind", wind_str, border=True)
    with mcols[1]:
        st.metric("🧭 Wind Dir", f"{current.get('winddirection', '—')}°", border=True)
    with mcols[2]:
        humidity = hourly.get("relative_humidity_2m", [None])[0]
        st.metric("💧 Humidity", f"{humidity}%" if humidity is not None else "—", border=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Reserved for compact widgets / small forecasts — currently empty to keep layout clean
    # (No right column, everything is centered and fits the body)
    # -----------------------------
# 7-day outlook
# -----------------------------
if show_daily and daily:
    st.subheader("🗓️ 7‑Day Outlook")
    st.markdown('<div class="weather-card">', unsafe_allow_html=True)
    
    daily_cols = st.columns(7)
    dates = pd.to_datetime(daily.get("time", []))
    t_max = daily.get("temperature_2m_max", [])
    t_min = daily.get("temperature_2m_min", [])
    codes = daily.get("weathercode", [])
    
    for i, (date, tmax, tmin, code) in enumerate(zip(dates, t_max, t_min, codes)):
        icon, desc = get_weather_icon(code)
        with daily_cols[i]:
            st.markdown(f"""
                <div style='text-align: center'>
                    <div style='color: #666'>{date.strftime('%a')}</div>
                    <div style='font-size: 2rem'>{icon}</div>
                    <div style='color: {temp_color(tmax)}'>{tmax:.1f}°</div>
                    <div style='color: #666'>{tmin:.1f}°</div>
                </div>
            """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)



# -----------------------------
# Wardrobe & Health — compact, modern, mobile-inspired
# -----------------------------
st.markdown("<div style='font-size:1.25rem;font-weight:700;margin-bottom:0.2em;margin-top:0.5em;'>🧭 Wardrobe & Health</div>", unsafe_allow_html=True)
now_temp = current.get("temperature")
now_wind = current.get("windspeed")
advice_bits: List[str] = []

if now_temp is not None:
    t = float(now_temp)
    if units.startswith("Imperial"):
        t = t * 9/5 + 32
    if (units.startswith("Metric") and t < 12) or (units.startswith("Imperial") and t < 54):
        advice_bits.append("🧥 Warm layer")
    elif (units.startswith("Metric") and t > 30) or (units.startswith("Imperial") and t > 86):
        advice_bits.append("🧢 Light & breathable; hydrate")
    else:
        advice_bits.append("👕 Light jacket or tee")

if now_wind is not None and float(now_wind) >= 30:
    advice_bits.append("💨 Windbreaker suggested")

if hourly:
    next_pop = hourly.get("precipitation_probability", [0])[0] or 0
    if next_pop >= 50 or (hourly.get("precipitation", [0])[0] or 0) > 0.1:
        advice_bits.append("🌂 Umbrella/waterproofs")
        if "Hate rain" in user_pref:
            advice_bits.append("⏰ Leave early to dodge showers")

if show_air and aq:
    ah = aq.get("hourly", {})
    if ah and ah.get("us_aqi"):
        aqi_now = ah.get("us_aqi")[0]
        if aqi_now is not None and not np.isnan(aqi_now):
            if aqi_now > 100 and "Runner" in user_pref:
                advice_bits.append("🏃‍♂️ Indoor workout (AQI)")
            if aqi_now > 150 and "Allergy-prone" in user_pref:
                advice_bits.append("😷 Mask outdoors (AQI)")

if daily:
    uvi_max = daily.get("uv_index_max", [0])[0]
    if uvi_max and uvi_max >= 6:
        advice_bits.append("🧴 High UV: SPF30+, sunglasses, hat")

if "Carry laptop" in user_pref and hourly:
    if (hourly.get("precipitation_probability", [0])[0] or 0) >= 30:
        advice_bits.append("💻 Rain cover for bag")

if advice_bits:
    st.markdown(
        "<div style='display:flex;flex-wrap:wrap;gap:0.5em 1em;margin-bottom:1em;'>"
        + "".join(f"<span style='background:#f1f5f9;border-radius:1em;padding:0.3em 0.9em;font-size:1.05rem;font-weight:500;'>{bit}</span>" for bit in dict.fromkeys(advice_bits))
        + "</div>", unsafe_allow_html=True)
else:
    st.markdown("<span style='color:#22c55e;font-size:1.1rem;font-weight:600;'>You're good to go! ✨</span>", unsafe_allow_html=True)

# -----------------------------
# Hourly charts & rain start detector
# -----------------------------
if show_hourly and hourly:
    ht = pd.to_datetime(hourly.get("time", []))
    hdf = pd.DataFrame({
        "time": ht,
        "temp": hourly.get("temperature_2m", []),
        "apparent": hourly.get("apparent_temperature", []),
        "precip": hourly.get("precipitation", []),
        "pop": hourly.get("precipitation_probability", []),
        "wind": hourly.get("windspeed_10m", []),
        "gust": hourly.get("windgusts_10m", []),
        "uv": hourly.get("uv_index", []),
        "cloud": hourly.get("cloud_cover", []),
        "weathercode": hourly.get("weathercode", []),
    }).set_index("time")

    st.subheader("📈 Next 48 hours")
    subdf = hdf.iloc[:48]

    # Rain start/stop detector with enhanced styling
    rain_mask = (subdf["precip"] > 0.05) | (subdf["pop"] >= 50)
    if rain_mask.any():
        first_rain_time = rain_mask.idxmax()
        rain_time_str = first_rain_time.strftime('%I:%M %p')
        st.markdown(
            f"""
            <div style="
            display: flex;
            align-items: center;
            background: #FEF9C3;
            border: 1px solid #FBBF24;
            border-radius: 4px;
            padding: 1rem 1.2rem;
            margin-bottom: 0.5rem;
            gap: 1rem;
            ">
            <div style="font-size:2.2rem;line-height:1">🌧️</div>
            <div>
                <div style="font-size:1.1rem;font-weight:700;color:#92400e;">Rain Expected</div>
                <div style="font-size:1rem;color:#92400e;">
                Rain likely starting at {rain_time_str}.
                </div>
            </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div style="
            display: flex;
            align-items: center;
            background: #F0FDF4;
            border: 1px solid #22C55E;
            border-radius: 4px;
            padding: 1rem 1.2rem;
            margin-bottom: 0.5rem;
            gap: 1rem;
            ">
            <div style="font-size:2.2rem;line-height:1">☀️</div>
            <div>
                <div style="font-size:1.1rem;font-weight:700;color:#166534;">Clear Weather</div>
                <div style="font-size:1rem;color:#334155;">
                No significant rain expected in the next 48 hours.
                </div>
            </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Enhanced temperature chart with custom colors
    fig1 = px.line(subdf.reset_index(), x="time", y=["temp", "apparent"],
                   title="Temperature vs Feels-like",
                   labels={"temp": "Temperature", "apparent": "Feels like"},
                   color_discrete_map={"temp": "#F87171", "apparent": "#60A5FA"})
    fig1.update_layout(hovermode="x unified")
    st.plotly_chart(fig1, use_container_width=True)

    # Enhanced precipitation chart
    fig2 = px.bar(subdf.reset_index(), x="time", y="pop",
                  title="Precipitation Probability (%)",
                  color_discrete_sequence=["#60A5FA"])
    st.plotly_chart(fig2, use_container_width=True)

    # Enhanced wind chart
    fig3 = px.line(subdf.reset_index(), x="time", y=["wind", "gust"],
                   title="Wind & Gusts",
                   labels={"wind": "Wind Speed", "gust": "Wind Gusts"},
                   color_discrete_map={"wind": "#34D399", "gust": "#F87171"})
    st.plotly_chart(fig3, use_container_width=True)

    


    # Daily temperature range chart
    # Build daily DataFrame safely: ensure all arrays are same length by trimming to the shortest series
    def _as_list(x):
        # Convert pandas Index/Series to plain list
        if x is None:
            return []
        try:
            return list(x)
        except Exception:
            return [x]
    
    series_map = {
        "date": _as_list(dates),
        "t_max": _as_list(t_max),
        "t_min": _as_list(t_min),
        "uv_max": _as_list(daily.get("uv_index_max", [])),
        "precip_sum": _as_list(daily.get("precipitation_sum", [])),
        "precip_hours": _as_list(daily.get("precipitation_hours", [])),
        "wind_max": _as_list(daily.get("windspeed_10m_max", [])),
    }
    
    # Determine minimum length and trim all series to that length
    lengths = {k: len(v) for k, v in series_map.items()}
    min_len = min(lengths.values()) if lengths else 0
    
    if min_len == 0:
        # No valid data — create empty DataFrame with the expected columns
        ddf = pd.DataFrame(columns=["date", "t_max", "t_min", "uv_max", "precip_sum", "precip_hours", "wind_max"])
    else:
        trimmed = {k: (pd.to_datetime(series_map[k][:min_len]) if k == "date" else series_map[k][:min_len]) for k in series_map}
        ddf = pd.DataFrame({
            "date": trimmed["date"],
            "t_max": trimmed["t_max"],
            "t_min": trimmed["t_min"],
            "uv_max": trimmed["uv_max"],
            "precip_sum": trimmed["precip_sum"],
            "precip_hours": trimmed["precip_hours"],
            "wind_max": trimmed["wind_max"],
        })

    figd = px.bar(ddf, x="date", y=["t_max", "t_min"],
                  barmode="group",
                  title="Daily Temperature Range",
                  labels={"t_max": "High", "t_min": "Low", "date": "Date"},
                  color_discrete_map={"t_max": "#F87171", "t_min": "#60A5FA"})
    st.plotly_chart(figd, use_container_width=True)

# -----------------------------
# Air Quality Panel
# -----------------------------
if show_air and aq:
    st.subheader("🫁 Air Quality")
    ah = aq.get("hourly", {})
    if ah:
        aqdf = pd.DataFrame({
            "time": pd.to_datetime(ah.get("time", [])),
            "pm2_5": ah.get("pm2_5", []),
            "pm10": ah.get("pm10", []),
            "o3": ah.get("ozone", []),
            "no2": ah.get("nitrogen_dioxide", []),
            "so2": ah.get("sulphur_dioxide", []),
            "co": ah.get("carbon_monoxide", []),
            "us_aqi": ah.get("us_aqi", []),
        }).set_index("time")

        latest = aqdf.iloc[0] if not aqdf.empty else None
        if latest is not None:
            if np.isnan(latest.get("us_aqi", np.nan)):
                # Fallback: compute AQI from PM2.5/PM10
                sub_pm25 = calc_aqi_subindex("pm2_5", latest.get("pm2_5", np.nan))
                sub_pm10 = calc_aqi_subindex("pm10", latest.get("pm10", np.nan))
                aqi_val = max([v for v in [sub_pm25, sub_pm10] if v is not None] or [np.nan])
            else:
                aqi_val = float(latest["us_aqi"]) if not np.isnan(latest["us_aqi"]) else np.nan

            if not np.isnan(aqi_val):
                cat = categorize_aqi(aqi_val)
                st.metric("US AQI (now)", f"{round(aqi_val)} — {cat}")
                st.caption(aqi_advice(aqi_val))

        figaq = px.line(aqdf.reset_index().iloc[:72], x="time", y=["pm2_5", "pm10"], title="PM2.5 & PM10 (next 72h)")
        st.plotly_chart(figaq, use_container_width=True)

        st.dataframe(aqdf.iloc[:48])


# -----------------------------
# Travel/Event checker
# -----------------------------
st.subheader("🧭 Quick Event Weather Check")
colA, colB = st.columns(2)
with colA:
    when = st.date_input("Event date", value=datetime.now().date())
with colB:
    hour = st.slider("Event hour (local)", 0, 23, value=datetime.now().hour)

if hourly:
    ht = pd.to_datetime(hourly.get("time", []))
    idx = (ht == pd.Timestamp(datetime.combine(when, datetime.min.time()) + timedelta(hours=hour)))
    if idx.any():
        row = pd.DataFrame(hourly).loc[list(idx)].iloc[0]
        et = row.get("temperature_2m", "—")
        ep = row.get("precipitation_probability", "—")
        ew = row.get("windspeed_10m", "—")
        st.info(f"At {when} {hour:02d}:00 — Temp: {et}°C, POP: {ep}%, Wind: {ew} km/h")
    else:
        st.caption("Hourly detail unavailable for that time.")

st.divider()

# Modern footer
st.markdown("""
    <div class='footer'>
        <b>ZainWeather</b> &mdash; Powered by Open‑Meteo Forecast, Geocoding & Air Quality APIs.<br>
        <span style='font-size:0.95rem;'>App is for informational purposes only. &copy; 2025</span>
    </div>
""", unsafe_allow_html=True)
