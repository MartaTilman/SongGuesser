import random

from services.metadata_cache import (
    add_song_to_cache,
    load_metadata_cache,
    save_metadata_cache,
    song_exists,
)
from services.song_parser import parse_song_from_title
from services.song_year_service import validate_song_year_for_decade
from services.youtube_service import (
    fetch_youtube_candidates_for_decade,
    is_global_2020s_candidate,
)


MIN_PARSE_CONFIDENCE = 75
MIN_TOTAL_SCORE = 70


def generate_start_time(duration_seconds):
    if duration_seconds <= 140:
        return random.randint(20, 35)

    if duration_seconds <= 220:
        return random.randint(25, 55)

    return random.randint(30, 70)


def get_min_parse_confidence(target_decade):
    if target_decade in ["50s", "60s"]:
        return 60

    if target_decade == "2020s":
        return 55

    return MIN_PARSE_CONFIDENCE


def get_min_total_score(target_decade):
    if target_decade in ["50s", "60s"]:
        return 55

    if target_decade == "2020s":
        return 50

    return MIN_TOTAL_SCORE


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


def extract_published_year(candidate):
    published_at = str(candidate.get("published_at") or "").strip()

    if len(published_at) >= 4 and published_at[:4].isdigit():
        return int(published_at[:4])

    return None


def build_fallback_year_result(candidate, target_decade):
    published_year = extract_published_year(candidate)

    if published_year is None:
        return None

    if year_to_decade(published_year) != target_decade:
        return None

    if target_decade != "2020s":
        return None

    if not is_global_2020s_candidate(candidate):
        return None

    return {
        "valid": True,
        "year": published_year,
        "confidence": 70,
        "source": "published_at_fallback",
        "decade": target_decade,
    }


def compute_final_score(candidate, parsed, year_result):
    score = candidate.get("pre_validation_score", 0)

    if parsed.get("is_real_song"):
        score += 20

    parse_confidence = parsed.get("confidence", 0)
    if parse_confidence >= 75:
        score += 20
    elif parse_confidence >= 60:
        score += 10
    elif parse_confidence >= 50:
        score += 5

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


def reject(target_decade, reason, candidate, extra=""):
    raw_title = candidate.get("raw_title", "")
    youtube_id = candidate.get("youtube_id", "")
    suffix = f" | {extra}" if extra else ""
    print(f"REJECT [{target_decade}] {reason} | id={youtube_id} | title={raw_title}{suffix}")
    return None


def validate_candidate(candidate, target_decade, cache):
    raw_title = candidate.get("raw_title", "")
    youtube_id = candidate.get("youtube_id")

    raw_lower = raw_title.lower()

    if "live" in raw_lower and target_decade not in ["50s", "60s"]:
        return reject(target_decade, "live_not_allowed", candidate)

    if not youtube_id or not raw_title:
        return reject(target_decade, "missing_id_or_title", candidate)

    if youtube_id in cache:
        return reject(target_decade, "youtube_id_already_in_cache", candidate)

    parsed = parse_song_from_title(raw_title)

    if not parsed.get("is_real_song", False):
        return reject(
            target_decade,
            "parser_rejected",
            candidate,
            extra=f"parse_source={parsed.get('source')}"
        )

    min_parse_confidence = get_min_parse_confidence(target_decade)
    parse_confidence = parsed.get("confidence", 0)
    if parse_confidence < min_parse_confidence:
        return reject(
            target_decade,
            "parse_confidence_too_low",
            candidate,
            extra=f"confidence={parse_confidence} min={min_parse_confidence}"
        )

    artist = parsed.get("artist", "").strip()
    title = parsed.get("title", "").strip()

    if not artist or not title:
        return reject(target_decade, "missing_artist_or_title_after_parse", candidate)

    year_result = validate_song_year_for_decade(
        artist=artist,
        title=title,
        target_decade=target_decade
    )

    if not year_result.get("valid", False):
        fallback_year_result = build_fallback_year_result(candidate, target_decade)

        if fallback_year_result is not None:
            print(
                "YEAR FALLBACK "
                f"[{target_decade}] | id={youtube_id} | title={raw_title} | "
                f"artist={artist} | parsed_title={title} | "
                f"fallback_year={fallback_year_result.get('year')}"
            )
            year_result = fallback_year_result
        else:
            return reject(
                target_decade,
                "year_validation_failed",
                candidate,
                extra=(
                    f"artist={artist} | parsed_title={title} | "
                    f"year={year_result.get('year')} | "
                    f"source={year_result.get('source')} | "
                    f"confidence={year_result.get('confidence')} | "
                    f"detected_decade={year_result.get('decade')}"
                )
            )

    year = year_result.get("year")
    if year is None:
        return reject(target_decade, "validated_year_missing", candidate)

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
        "parse_confidence": parse_confidence,
        "parse_source": parsed.get("source"),
        "year_confidence": year_result.get("confidence", 0),
        "year_source": year_result.get("source"),
        "pre_validation_score": candidate.get("pre_validation_score", 0),
    }

    if song_exists(cache, song):
        return reject(
            target_decade,
            "same_song_already_exists",
            candidate,
            extra=f"artist={artist} | parsed_title={title} | year={year}"
        )

    final_score = compute_final_score(candidate, parsed, year_result)
    song["final_score"] = final_score

    min_total_score = get_min_total_score(target_decade)
    if final_score < min_total_score:
        return reject(
            target_decade,
            "final_score_too_low",
            candidate,
            extra=f"score={final_score} min={min_total_score}"
        )

    print(
        "ACCEPT "
        f"[{target_decade}] | id={youtube_id} | artist={artist} | title={title} | "
        f"year={year} | parse_source={parsed.get('source')} | "
        f"year_source={year_result.get('source')} | final_score={final_score}"
    )

    return song


def discover_songs_for_decade(decade, target_count=10, max_results_per_query=15):
    cache = load_metadata_cache()

    existing_for_decade = [
        song for song in cache.values()
        if song.get("decade") == decade
    ]

    if len(existing_for_decade) >= target_count:
        print(f"{decade}: discovery skipped, cache already has {len(existing_for_decade)} songs")
        return existing_for_decade

    candidates = fetch_youtube_candidates_for_decade(
        decade=decade,
        max_results_per_query=max_results_per_query
    )

    print(f"{decade}: validating {len(candidates)} candidates after YouTube stage")

    added_songs = []

    for candidate in candidates:
        validated_song = validate_candidate(candidate, decade, cache)

        if validated_song is None:
            continue

        was_added = add_song_to_cache(cache, validated_song)

        if was_added:
            added_songs.append(validated_song)
            print(
                f"{decade}: added {validated_song.get('artist')} - "
                f"{validated_song.get('title')} ({validated_song.get('year')})"
            )

        current_total = len([
            song for song in cache.values()
            if song.get("decade") == decade
        ])

        if current_total >= target_count:
            break

    save_metadata_cache(cache)

    final_songs = [
        song for song in cache.values()
        if song.get("decade") == decade
    ]

    print(f"{decade}: added_this_run={len(added_songs)} | final_total={len(final_songs)}")

    return final_songs
