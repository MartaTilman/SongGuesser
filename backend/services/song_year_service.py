import json
import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

USE_OPENAI = os.getenv("USE_OPENAI", "true").lower() == "true"

client = None
if USE_OPENAI:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    except Exception as e:
        print(f"OpenAI client init error in song_year_service: {e}")
        client = None


def year_to_decade(year):
    if year is None:
        return None

    if 1950 <= year <= 1959:
        return "50s"
    if 1960 <= year <= 1969:
        return "60s"
    if 1970 <= year <= 1979:
        return "70s"
    if 1980 <= year <= 1989:
        return "80s"
    if 1990 <= year <= 1999:
        return "90s"
    if 2000 <= year <= 2009:
        return "2000s"
    if 2010 <= year <= 2019:
        return "2010s"
    if 2020 <= year <= 2029:
        return "2020s"

    return None


def extract_year_from_text(text):
    if not text:
        return None

    match = re.search(r"\b(19[5-9]\d|20[0-2]\d)\b", str(text))
    if match:
        return int(match.group(1))

    return None


def get_song_year_from_musicbrainz(artist, title):
    url = "https://musicbrainz.org/ws/2/recording/"
    params = {
        "query": f'artist:"{artist}" recording:"{title}"',
        "fmt": "json",
        "limit": 5
    }

    headers = {
        "User-Agent": "song-guesser/1.0 (student project)"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=6)
        response.raise_for_status()
        data = response.json()

        recordings = data.get("recordings", [])
        if not recordings:
            return None

        for rec in recordings:
            first_release = rec.get("first-release-date")
            year = extract_year_from_text(first_release)

            if year is not None:
                return {
                    "year": year,
                    "confidence": 90,
                    "source": "musicbrainz"
                }

    except Exception as e:
        print(f"MusicBrainz error: {e}")

    return None


def get_song_year_with_ai(artist, title):
    if not USE_OPENAI or client is None:
        return None

    prompt = f"""
You are helping validate metadata for a music quiz game.

Task:
Determine the original release year of this song.

Artist: {artist}
Song title: {title}

Return ONLY valid JSON in this exact format:
{{
  "year": 1985,
  "confidence": 0
}}

Rules:
- year must be a single integer
- confidence must be an integer from 0 to 100
- if unsure, use lower confidence
- if you cannot reasonably determine the year, return:
{{
  "year": null,
  "confidence": 0
}}
- do not include any explanation outside JSON
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        text = response.choices[0].message.content.strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)

        if not match:
            return None

        parsed = json.loads(match.group())

        year = parsed.get("year")
        confidence = parsed.get("confidence", 0)

        if year is not None:
            try:
                year = int(year)
            except Exception:
                year = None

        try:
            confidence = int(confidence)
        except Exception:
            confidence = 0

        return {
            "year": year,
            "confidence": confidence,
            "source": "ai"
        }

    except Exception as e:
        print(f"OpenAI year error: {e}")
        return None


def get_song_year(artist, title):
    result = get_song_year_from_musicbrainz(artist, title)
    if result is not None and result.get("year") is not None:
        return result

    result = get_song_year_with_ai(artist, title)
    if result is not None and result.get("year") is not None:
        return result

    return {
        "year": None,
        "confidence": 0,
        "source": "fallback"
    }


def validate_song_year_for_decade(artist, title, target_decade):
    result = get_song_year(artist, title)

    year = result.get("year")
    confidence = result.get("confidence", 0)

    if year is None:
        return {
            "valid": False,
            "year": None,
            "confidence": confidence,
            "source": result.get("source"),
            "decade": None
        }

    decade = year_to_decade(year)

    if decade != target_decade:
        return {
            "valid": False,
            "year": year,
            "confidence": confidence,
            "source": result.get("source"),
            "decade": decade
        }

    min_confidence = 60 if result.get("source") == "ai" else 0

    if confidence < min_confidence:
        return {
            "valid": False,
            "year": year,
            "confidence": confidence,
            "source": result.get("source"),
            "decade": decade
        }

    return {
        "valid": True,
        "year": year,
        "confidence": confidence,
        "source": result.get("source"),
        "decade": decade
    }