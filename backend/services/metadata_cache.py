import json
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

try:
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:
    psycopg = None
    Jsonb = None


BACKEND_DIR = Path(__file__).resolve().parent.parent
CACHE_FILE = BACKEND_DIR / "song_metadata_cache.json"
BACKUP_FILE = BACKEND_DIR / "song_metadata_cache.json.bak"

load_dotenv(BACKEND_DIR / ".env")


def get_database_url():
    return os.getenv("DATABASE_URL")


def should_use_database():
    return bool(get_database_url())


def connect_to_database():
    if psycopg is None:
        raise RuntimeError("DATABASE_URL is set, but psycopg is not installed.")

    return psycopg.connect(get_database_url())


def ensure_song_cache_table(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS song_metadata_cache (
                youtube_id TEXT PRIMARY KEY,
                artist TEXT,
                title TEXT,
                decade TEXT,
                year INTEGER,
                metadata JSONB NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )


def load_metadata_cache_from_file():
    source_file = CACHE_FILE

    if not os.path.exists(source_file) and os.path.exists(BACKUP_FILE):
        source_file = BACKUP_FILE

    if not os.path.exists(source_file):
        return {}

    try:
        with open(source_file, "r", encoding="utf-8") as f:
            data = json.load(f)

            if isinstance(data, dict):
                return data

            return {}

    except Exception as e:
        print(f"Greska pri ucitavanju lokalnog cachea: {e}")
        return {}


def load_metadata_cache_from_database():
    with connect_to_database() as conn:
        ensure_song_cache_table(conn)

        with conn.cursor() as cur:
            cur.execute("SELECT youtube_id, metadata FROM song_metadata_cache")
            rows = cur.fetchall()

    cache = {}

    for youtube_id, metadata in rows:
        if isinstance(metadata, dict):
            cache[youtube_id] = metadata

    return cache


def save_metadata_cache_to_file(cache, allow_deletions=False):
    cache_to_save = cache

    if not allow_deletions:
        existing_cache = load_metadata_cache_from_file()
        cache_to_save = {
            **existing_cache,
            **cache
        }

    if os.path.exists(CACHE_FILE):
        shutil.copy2(CACHE_FILE, BACKUP_FILE)

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_to_save, f, ensure_ascii=False, indent=2)


def save_metadata_cache_to_database(cache, allow_deletions=False):
    with connect_to_database() as conn:
        ensure_song_cache_table(conn)

        with conn.cursor() as cur:
            if allow_deletions:
                cur.execute("TRUNCATE TABLE song_metadata_cache")

            rows = []
            for youtube_id, song in cache.items():
                if not youtube_id or not isinstance(song, dict):
                    continue

                rows.append((
                    youtube_id,
                    song.get("artist"),
                    song.get("title"),
                    song.get("decade"),
                    song.get("year"),
                    Jsonb(song)
                ))

            if rows:
                cur.executemany(
                    """
                    INSERT INTO song_metadata_cache (
                        youtube_id,
                        artist,
                        title,
                        decade,
                        year,
                        metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (youtube_id) DO UPDATE SET
                        artist = EXCLUDED.artist,
                        title = EXCLUDED.title,
                        decade = EXCLUDED.decade,
                        year = EXCLUDED.year,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    """,
                    rows
                )


def load_metadata_cache():
    if should_use_database():
        try:
            database_cache = load_metadata_cache_from_database()

            if database_cache:
                return database_cache

            file_cache = load_metadata_cache_from_file()
            if file_cache:
                save_metadata_cache_to_database(file_cache)
                print("Song metadata cache seeded into database from local JSON.")

            return file_cache

        except Exception as e:
            print(f"Greska pri ucitavanju cachea iz baze: {e}")

    return load_metadata_cache_from_file()


def save_metadata_cache(cache, allow_deletions=False):
    try:
        if should_use_database():
            try:
                save_metadata_cache_to_database(cache, allow_deletions=allow_deletions)
                return
            except Exception as e:
                print(f"Greska pri spremanju cachea u bazu: {e}")

        save_metadata_cache_to_file(cache, allow_deletions=allow_deletions)
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
