import json
import os
import random
import re
import time
from difflib import SequenceMatcher
from html import unescape

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


def normalize_text(value):
    text = unescape(str(value or "")).lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def simplify_text(value):
    text = normalize_text(value)
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"\[[^\]]*\]", " ", text)
    text = re.sub(r"\b(feat|ft|featuring)\b.*$", "", text).strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def similarity(a, b):
    if not a or not b:
        return 0.0

    return SequenceMatcher(None, a, b).ratio()


def score_musicbrainz_recording(recording, artist, title):
    target_artist = simplify_text(artist)
    target_title = simplify_text(title)

    recording_title = simplify_text(recording.get("title", ""))
    artist_credit = " ".join(
        credit.get("name", "")
        for credit in recording.get("artist-credit", [])
        if isinstance(credit, dict)
    )
    recording_artist = simplify_text(artist_credit)

    title_score = similarity(target_title, recording_title)
    artist_score = similarity(target_artist, recording_artist)

    first_release = recording.get("first-release-date")
    year = extract_year_from_text(first_release)
    if year is None:
        return None

    base_score = int(recording.get("score", 0))
    combined = (title_score * 0.45) + (artist_score * 0.45) + ((min(base_score, 100) / 100) * 0.10)

    if title_score < 0.72 or artist_score < 0.72:
        return None

    return {
        "year": year,
        "confidence": max(0, min(100, int(round(combined * 100)))),
        "source": "musicbrainz",
        "title_score": title_score,
        "artist_score": artist_score,
    }


def extract_artist_credit(recording):
    return " ".join(
        credit.get("name", "")
        for credit in recording.get("artist-credit", [])
        if isinstance(credit, dict)
    ).strip()


def decade_to_year_range(decade):
    ranges = {
        "50s": (1950, 1959),
        "60s": (1960, 1969),
        "70s": (1970, 1979),
        "80s": (1980, 1989),
        "90s": (1990, 1999),
        "2000s": (2000, 2009),
        "2010s": (2010, 2019),
        "2020s": (2020, 2026),
    }
    return ranges.get(decade)


def musicbrainz_request(params, attempts=3):
    url = "https://musicbrainz.org/ws/2/recording/"
    headers = {
        "User-Agent": "song-guesser/1.0 (student project)"
    }

    for attempt in range(attempts):
        try:
            time.sleep(1.2)
            response = requests.get(url, params=params, headers=headers, timeout=8)

            if response.status_code == 503:
                print(f"MusicBrainz temporary unavailable (attempt {attempt + 1}/{attempts})")
                time.sleep(3 + attempt)
                continue

            if response.status_code == 429:
                print(f"MusicBrainz rate limited (attempt {attempt + 1}/{attempts})")
                time.sleep(5 + attempt)
                continue

            response.raise_for_status()
            return response.json()

        except Exception as e:
            print(f"MusicBrainz error: {e}")
            time.sleep(3 + attempt)

    return None


def recording_to_song_candidate(recording, target_decade):
    title = str(recording.get("title") or "").strip()
    artist = extract_artist_credit(recording)
    year = extract_year_from_text(recording.get("first-release-date"))

    if not title or not artist or year is None:
        return None

    if year_to_decade(year) != target_decade:
        return None

    title_clean = simplify_text(title)
    artist_clean = simplify_text(artist)

    if not title_clean or not artist_clean:
        return None

    if len(title_clean) < 3 or len(artist_clean) < 2:
        return None

    disallowed_title_words = {
        "interview",
        "medley",
        "karaoke",
        "commentary",
        "dialogue",
        "demo",
        "outtake",
    }

    if any(word in title_clean.split() for word in disallowed_title_words):
        return None

    try:
        mb_score = int(recording.get("score", 0))
    except Exception:
        mb_score = 0

    return {
        "artist": artist,
        "title": title,
        "year": year,
        "musicbrainz_id": recording.get("id"),
        "musicbrainz_score": mb_score,
    }


def fetch_musicbrainz_songs_for_decade(decade, limit=25):
    year_range = decade_to_year_range(decade)
    if year_range is None:
        return []

    start_year, end_year = year_range
    offset = random.choice([0, 25, 50, 75])
    query = (
        f'firstreleasedate:[{start_year}-01-01 TO {end_year}-12-31] '
        'AND type:single'
    )

    data = musicbrainz_request({
        "query": query,
        "fmt": "json",
        "limit": limit,
        "offset": offset,
    })

    if not data:
        return []

    songs = []
    seen = set()

    for recording in data.get("recordings", []):
        candidate = recording_to_song_candidate(recording, decade)
        if candidate is None:
            continue

        identity = (
            simplify_text(candidate["artist"]),
            simplify_text(candidate["title"]),
            candidate["year"],
        )

        if identity in seen:
            continue

        seen.add(identity)
        songs.append(candidate)

    songs.sort(
        key=lambda item: item.get("musicbrainz_score", 0),
        reverse=True,
    )

    print(f"{decade}: musicbrainz song candidates={len(songs)}")
    return songs


def get_song_year_from_musicbrainz(artist, title):
    data = musicbrainz_request({
        "query": f'artist:"{artist}" recording:"{title}"',
        "fmt": "json",
        "limit": 10,
    })

    if not data:
        return None

    recordings = data.get("recordings", [])
    if not recordings:
        return None

    scored_results = []

    for rec in recordings:
        scored = score_musicbrainz_recording(rec, artist, title)
        if scored is not None:
            scored_results.append(scored)

    if not scored_results:
        return None

    scored_results.sort(
        key=lambda item: (
            item.get("confidence", 0),
            item.get("title_score", 0),
            item.get("artist_score", 0),
        ),
        reverse=True,
    )

    best = scored_results[0]

    if best["confidence"] < 80:
        return None

    return {
        "year": best["year"],
        "confidence": best["confidence"],
        "source": "musicbrainz",
    }


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
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
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
            "source": "ai",
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
        "source": "fallback",
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
            "decade": None,
        }

    decade = year_to_decade(year)

    if decade != target_decade:
        return {
            "valid": False,
            "year": year,
            "confidence": confidence,
            "source": result.get("source"),
            "decade": decade,
        }

    min_confidence = 75 if result.get("source") == "ai" else 80

    if confidence < min_confidence:
        return {
            "valid": False,
            "year": year,
            "confidence": confidence,
            "source": result.get("source"),
            "decade": decade,
        }

    return {
        "valid": True,
        "year": year,
        "confidence": confidence,
        "source": result.get("source"),
        "decade": decade,
    }
