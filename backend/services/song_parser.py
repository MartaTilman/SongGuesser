import json
import os
import re
from html import unescape

from dotenv import load_dotenv

load_dotenv()

USE_OPENAI = os.getenv("USE_OPENAI", "true").lower() == "true"

client = None
if USE_OPENAI:
    try:
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    except Exception as e:
        print(f"OpenAI client init error: {e}")
        client = None


BAD_TITLE_HINTS = [
    "cover",
    "karaoke",
    "remix",
    "reaction",
    "tribute",
    "concert",
    "jukebox",
    "playlist",
    "compilation",
    "mix",
    "shorts",
    "#shorts",
    "sped up",
    "slowed",
    "reverb",
    "instrumental",
    "lyrics",
    "full album",
    "medley",
    "teaser",
    "trailer",
    "tutorial",
    "greatest hits",
    "best songs",
    "top 10",
    "top 20",
    "most recognizable",
    "non stop",
    "mega hits",
]

FEATURE_SEPARATORS = [
    " feat. ",
    " feat ",
    " ft. ",
    " ft ",
    " featuring ",
]


def normalize_for_compare(value):
    text = unescape(str(value or ""))
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def cleanup_title(youtube_title):
    cleaned = unescape(str(youtube_title or ""))

    cleaned = re.sub(r"\(.*?\)", "", cleaned)
    cleaned = re.sub(r"\[.*?\]", "", cleaned)
    cleaned = re.sub(r"\{.*?\}", "", cleaned)

    replacements = [
        "Official Video",
        "OFFICIAL VIDEO",
        "Official Music Video",
        "official video",
        "official music video",
        "Official Audio",
        "official audio",
        "HD",
        "4K",
        "TopPop",
        "• TopPop",
        "| TopPop",
        "Remastered",
        "remastered",
        "Mono",
        "mono",
        "Stereo",
        "stereo",
        "HQ",
        "Lyrics",
        "lyric video",
        "LYRIC VIDEO",
    ]

    for item in replacements:
        cleaned = cleaned.replace(item, "")

    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned


def strip_featured_artists(value):
    text = str(value or "").strip()
    lowered = text.lower()

    for separator in FEATURE_SEPARATORS:
        index = lowered.find(separator)
        if index != -1:
            return text[:index].strip(" -–|,")

    return text.strip(" -–|,")


def is_plausible_artist_title(artist, title):
    artist_clean = strip_featured_artists(artist)
    title_clean = str(title or "").strip()

    if not artist_clean or not title_clean:
        return False

    lowered_artist = normalize_for_compare(artist_clean)
    lowered_title = normalize_for_compare(title_clean)

    if len(lowered_artist) < 2 or len(lowered_title) < 2:
        return False

    banned_title_patterns = [
        r"\b\d{4}s\b",
        r"\bmmxx\b",
        r"\bofficial video\b",
        r"\bofficial audio\b",
        r"\bfull album\b",
        r"\bplaylist\b",
        r"\bcompilation\b",
    ]

    if any(re.search(pattern, lowered_title) for pattern in banned_title_patterns):
        return False

    if re.fullmatch(r"\d{4}", lowered_title):
        return False

    if lowered_artist == lowered_title:
        return False

    return True


def looks_like_bad_candidate(youtube_title):
    lowered = normalize_for_compare(youtube_title)

    for hint in BAD_TITLE_HINTS:
        if hint in lowered:
            return True

    return False


def parse_song_with_regex(youtube_title):
    cleaned = cleanup_title(youtube_title)

    patterns = [
        r"^(?P<artist>.+?)\s*-\s*(?P<title>.+)$",
        r"^(?P<artist>.+?)\s*:\s*(?P<title>.+)$",
    ]

    for pattern in patterns:
        match = re.match(pattern, cleaned)
        if match:
            artist = strip_featured_artists(match.group("artist"))
            title = match.group("title").strip(" -–|")

            if is_plausible_artist_title(artist, title):
                return {
                    "artist": artist,
                    "title": title,
                    "is_real_song": True,
                    "confidence": 78,
                    "source": "regex",
                }

    return None


def parse_song_with_ai(youtube_title):
    if not USE_OPENAI or client is None:
        return None

    prompt = f"""
You are validating a YouTube video title for a music quiz game.

Task:
1. Determine whether this title most likely refers to ONE real song, not a compilation, playlist, reaction, remix, karaoke, live performance, medley, shorts clip, tutorial, or other non-standard result.
2. Extract the main artist and main song title if possible.

Return ONLY valid JSON in this exact format:
{{
  "artist": "string",
  "title": "string",
  "is_real_song": true,
  "confidence": 0
}}

Rules:
- confidence must be an integer from 0 to 100
- if this does NOT look like one real song, set is_real_song to false
- if uncertain, lower confidence
- do not include extra text

YouTube title:
{youtube_title}
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

        artist = strip_featured_artists(parsed.get("artist", ""))
        title = str(parsed.get("title", "")).strip()
        is_real_song = bool(parsed.get("is_real_song", False))

        try:
            confidence = int(parsed.get("confidence", 0))
        except Exception:
            confidence = 0

        if not is_real_song or not is_plausible_artist_title(artist, title):
            return {
                "artist": "",
                "title": "",
                "is_real_song": False,
                "confidence": 0,
                "source": "ai_rejected",
            }

        return {
            "artist": artist,
            "title": title,
            "is_real_song": True,
            "confidence": confidence,
            "source": "ai",
        }

    except Exception as e:
        print(f"OpenAI parse error: {e}")
        return None


def parse_song_from_title(youtube_title):
    if looks_like_bad_candidate(youtube_title):
        return {
            "artist": "",
            "title": "",
            "is_real_song": False,
            "confidence": 0,
            "source": "blacklist",
        }

    regex_result = parse_song_with_regex(youtube_title)
    if regex_result is not None:
        return regex_result

    ai_result = parse_song_with_ai(youtube_title)
    if ai_result is not None:
        return ai_result

    return {
        "artist": "",
        "title": "",
        "is_real_song": False,
        "confidence": 0,
        "source": "fallback",
    }
