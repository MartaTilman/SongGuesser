import json
import os

CACHE_FILE = "song_metadata_cache.json"


def load_metadata_cache():
    if not os.path.exists(CACHE_FILE):
        return {}

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

            if isinstance(data, dict):
                return data

            return {}

    except Exception as e:
        print(f"Greška pri učitavanju cachea: {e}")
        return {}


def save_metadata_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Greška pri spremanju cachea: {e}")


def normalize_text(value):
    if value is None:
        return ""

    return str(value).strip().lower()


def song_exists(cache, song):
    youtube_id = song.get("youtube_id")
    if youtube_id and youtube_id in cache:
        return True

    new_artist = normalize_text(song.get("artist"))
    new_title = normalize_text(song.get("title"))
    new_year = song.get("year")

    for cached_song in cache.values():
        cached_artist = normalize_text(cached_song.get("artist"))
        cached_title = normalize_text(cached_song.get("title"))
        cached_year = cached_song.get("year")

        if (
            cached_artist == new_artist
            and cached_title == new_title
            and cached_year == new_year
        ):
            return True

    return False


def add_song_to_cache(cache, song):
    youtube_id = song.get("youtube_id")

    if not youtube_id:
        return False

    if song_exists(cache, song):
        return False

    cache[youtube_id] = song
    return True


def get_songs_by_decade(cache, decade):
    return [
        song for song in cache.values()
        if song.get("decade") == decade
    ]