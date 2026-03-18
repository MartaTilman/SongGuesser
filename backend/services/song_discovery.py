import random

from services.metadata_cache import (
    load_metadata_cache,
    save_metadata_cache,
    add_song_to_cache,
    song_exists,
)
from services.song_parser import parse_song_from_title
from services.song_year_service import validate_song_year_for_decade
from services.youtube_service import fetch_youtube_candidates_for_decade


MIN_PARSE_CONFIDENCE = 75
MIN_TOTAL_SCORE = 70


def generate_start_time(duration_seconds):
    if duration_seconds <= 140:
        return random.randint(20, 35)

    if duration_seconds <= 220:
        return random.randint(25, 55)

    return random.randint(30, 70)


def compute_final_score(candidate, parsed, year_result):
    score = candidate.get("pre_validation_score", 0)

    if parsed.get("is_real_song"):
        score += 20

    parse_confidence = parsed.get("confidence", 0)
    if parse_confidence >= 75:
        score += 20
    elif parse_confidence >= 60:
        score += 10

    if year_result.get("valid"):
        score += 25

    year_confidence = year_result.get("confidence", 0)
    if year_confidence >= 85:
        score += 10
    elif year_confidence >= 75:
        score += 5

    if candidate.get("view_count", 0) >= 10_000_000:
        score += 10
    elif candidate.get("view_count", 0) >= 1_000_000:
        score += 5

    return score


def validate_candidate(candidate, target_decade, cache):
    raw_title = candidate.get("raw_title", "")
    youtube_id = candidate.get("youtube_id")

    raw_lower = raw_title.lower()

   
    if "live" in raw_lower:
        if target_decade not in ["50s", "60s"]:
            print(f"REJECT [{target_decade}] live not allowed: {raw_title}")
            return None
        
    if not youtube_id or not raw_title:
        return None

    if youtube_id in cache:
        return None

    parsed = parse_song_from_title(raw_title)

    if not parsed.get("is_real_song", False):
        return None

    if parsed.get("confidence", 0) < MIN_PARSE_CONFIDENCE:
        return None

    artist = parsed.get("artist", "").strip()
    title = parsed.get("title", "").strip()

    if not artist or not title:
        return None

    year_result = validate_song_year_for_decade(
        artist=artist,
        title=title,
        target_decade=target_decade
    )

    if not year_result.get("valid", False):
        return None

    year = year_result.get("year")
    if year is None:
        return None

    song = {
        "artist": artist,
        "title": title,
        "youtube_id": youtube_id,
        "start_time": generate_start_time(candidate.get("duration_seconds", 180)),
        "decade": target_decade,
        "year": year,
        "channel_title": candidate.get("channel_title"),
        "view_count": candidate.get("view_count", 0),
        "duration_seconds": candidate.get("duration_seconds", 0),
        "published_at": candidate.get("published_at"),
        "source_query": candidate.get("source_query"),
        "parse_confidence": parsed.get("confidence", 0),
        "parse_source": parsed.get("source"),
        "year_confidence": year_result.get("confidence", 0),
        "year_source": year_result.get("source"),
        "pre_validation_score": candidate.get("pre_validation_score", 0),
    }

    if song_exists(cache, song):
        return None

    final_score = compute_final_score(candidate, parsed, year_result)
    song["final_score"] = final_score

    if final_score < MIN_TOTAL_SCORE:
        return None

    return song


def discover_songs_for_decade(decade, target_count=10, max_results_per_query=15):
    cache = load_metadata_cache()

    existing_for_decade = [
        song for song in cache.values()
        if song.get("decade") == decade
    ]

    if len(existing_for_decade) >= target_count:
        return existing_for_decade

    candidates = fetch_youtube_candidates_for_decade(
        decade=decade,
        max_results_per_query=max_results_per_query
    )

    added_songs = []

    for candidate in candidates:
        validated_song = validate_candidate(candidate, decade, cache)

        if validated_song is None:
            continue

        was_added = add_song_to_cache(cache, validated_song)

        if was_added:
            added_songs.append(validated_song)

        current_total = len([
            song for song in cache.values()
            if song.get("decade") == decade
        ])

        if current_total >= target_count:
            break

    save_metadata_cache(cache)

    return [
        song for song in cache.values()
        if song.get("decade") == decade
    ]