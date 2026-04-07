"""
AgriSpark 2.0 — Weather Integration
Uses Open-Meteo (free, no key needed) to get 7-day forecast summary.
"""

import requests


# Thai province name → lat/lon approximate centers
_PROVINCE_COORDS = {
    "chiang mai":   (18.79, 98.98),
    "chiang rai":   (19.91, 99.83),
    "bangkok":      (13.75, 100.52),
    "khon kaen":    (16.44, 102.84),
    "udon thani":   (17.41, 102.79),
    "nakhon ratchasima": (14.97, 102.10),
    "surin":        (14.88, 103.49),
    "roi et":       (16.05, 103.65),
    "lampang":      (18.29, 99.49),
    "phrae":        (18.15, 100.14),
    "nan":          (18.78, 100.77),
    "chiang dao":   (19.37, 98.96),
    "pai":          (19.36, 98.43),
    "sukhothai":    (17.00, 99.82),
    "phetchabun":   (16.42, 101.16),
    "ubon ratchathani": (15.24, 104.85),
    "nong khai":    (17.87, 102.74),
    "loei":         (17.48, 101.73),
    "nakhon sawan": (15.70, 100.13),
    "rayong":       (12.68, 101.27),
    "chonburi":     (13.36, 100.99),
    "pattaya":      (12.93, 100.88),
    "phuket":       (7.89, 98.40),
    "krabi":        (8.06, 98.91),
    "hat yai":      (7.01, 100.47),
    "songkhla":     (7.19, 100.59),
    "surat thani":  (9.14, 99.33),
}

_DEFAULT_COORDS = (15.87, 100.99)   # approximate center of Thailand


def _get_coords(location: str) -> tuple:
    """Try to match location string to known coordinates."""
    loc_lower = location.lower().strip()
    for key, coords in _PROVINCE_COORDS.items():
        if key in loc_lower or loc_lower in key:
            return coords
    return _DEFAULT_COORDS


def get_weather_summary(location: str) -> str:
    """Fetch 7-day forecast and return a human-readable summary."""
    lat, lon = _get_coords(location)
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,"
        f"weathercode&timezone=Asia%2FBangkok&forecast_days=7"
    )
    try:
        headers = {"User-Agent": "AgriSpark/2.0 (Smallholder Advisory App)"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("daily", {})

        lines = []
        dates  = data.get("time", [])
        t_max  = data.get("temperature_2m_max", [])
        t_min  = data.get("temperature_2m_min", [])
        rain   = data.get("precipitation_sum", [])

        for i in range(min(7, len(dates))):
            day_rain = rain[i] if rain[i] else 0
            lines.append(
                f"{dates[i]}: {t_min[i]}–{t_max[i]}°C, Rain: {day_rain:.1f}mm"
            )

        total_rain = sum(r for r in rain if r)
        summary = "; ".join(lines[:3]) + f" ... Total week rain: {total_rain:.1f}mm"
        return summary

    except Exception as e:
        print(f"Weather Fetch Error: {e}")
        # Provide a realistic generic baseline so the AI can still give practical advice
        return "Weather API offline. Assume standard seasonal tropical climate: 24–33°C, intermittent rains, moderate humidity."
