import json
import os
import shutil
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
CACHE_FILE = BACKEND_DIR / "song_metadata_cache.json"
BACKUP_FILE = BACKEND_DIR / "song_metadata_cache.json.bak"


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
        print(f"Greska pri ucitavanju cachea: {e}")
        return {}


def save_metadata_cache(cache, allow_deletions=False):
    try:
        cache_to_save = cache

        if not allow_deletions:
            existing_cache = load_metadata_cache()
            cache_to_save = {
                **existing_cache,
                **cache
            }

        if os.path.exists(CACHE_FILE):
            shutil.copy2(CACHE_FILE, BACKUP_FILE)

        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Greska pri spremanju cachea: {e}")


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
