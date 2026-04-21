import random

from services.metadata_cache import load_metadata_cache, save_metadata_cache
from services.song_discovery import discover_songs_for_decade
from services.youtube_service import find_replacement_video_for_song, is_video_embeddable


class SongCache:
    def __init__(self):
        self.cache = {
            "50s": [],
            "60s": [],
            "70s": [],
            "80s": [],
            "90s": [],
            "2000s": [],
            "2010s": [],
            "2020s": []
        }
        self.youtube_quota_exceeded = False

    def generate_start_time(self, duration_seconds):
        if duration_seconds <= 140:
            return random.randint(20, 35)

        if duration_seconds <= 220:
            return random.randint(25, 55)

        return random.randint(30, 70)

    def load_from_metadata_cache(self):
        metadata_cache = load_metadata_cache()

        for decade in self.cache.keys():
            self.cache[decade] = []

        for song in metadata_cache.values():
            decade = song.get("decade")
            if decade in self.cache:
                self.cache[decade].append(song)

    def get_decades_sorted_by_priority(self):
        return sorted(
            self.cache.keys(),
            key=lambda decade: len(self.cache[decade])
        )

    def fill_cache(self, min_songs_per_decade=5):
        print("Checking song cache...")

        self.load_from_metadata_cache()
        priority_decades = self.get_decades_sorted_by_priority()

        for decade in priority_decades:
            current_count = len(self.cache[decade])

            if current_count >= min_songs_per_decade:
                print(f"{decade}: already has {current_count} songs")
                continue

            if self.youtube_quota_exceeded:
                print(f"{decade}: skipping discovery because YouTube quota is exceeded")
                break

            print(f"Loading songs for {decade}... current={current_count}, target={min_songs_per_decade}")

            try:
                discovered = discover_songs_for_decade(
                    decade=decade,
                    target_count=min_songs_per_decade,
                    max_results_per_query=12
                )
                self.cache[decade] = discovered
                print(f"{decade}: total {len(self.cache[decade])} songs in cache")

            except Exception as e:
                error_text = str(e).lower()

                if "quota" in error_text or "quotaexceeded" in error_text:
                    self.youtube_quota_exceeded = True
                    print("YouTube quota exceeded. Stopping further discovery attempts.")
                    break
                else:
                    print(f"Discovery failed for {decade}: {e}")

        print("Song cache ready!")

    def refill_decade_if_needed(self, decade, min_count=5):
        current_count = len(self.cache.get(decade, []))

        if current_count >= min_count:
            return

        if self.youtube_quota_exceeded:
            print(f"Skipping refill for {decade} because YouTube quota is exceeded")
            return

        print(f"Refilling decade {decade} because only {current_count} songs are available...")

        try:
            discovered = discover_songs_for_decade(
                decade=decade,
                target_count=max(min_count, 5),
                max_results_per_query=12
            )
            self.cache[decade] = discovered
            print(f"{decade}: total {len(self.cache[decade])} songs after refill")
        except Exception as e:
            error_text = str(e).lower()

            if "quota" in error_text or "quotaexceeded" in error_text:
                self.youtube_quota_exceeded = True
                print("YouTube quota exceeded during refill. Further discovery disabled.")
            else:
                print(f"Refill failed for {decade}: {e}")

    def get_available_decades(self, min_ready_count=5):
        ready = []

        for decade, songs in self.cache.items():
            valid_count = len([
                song for song in songs
                if song.get("youtube_id")
                and song.get("artist")
                and song.get("title")
                and song.get("year") is not None
            ])

            if valid_count >= min_ready_count:
                ready.append(decade)

        return ready

    def replace_song_video(self, song, replacement):
        old_youtube_id = song.get("youtube_id")
        new_youtube_id = replacement.get("youtube_id")

        if not old_youtube_id or not new_youtube_id:
            return False

        song["youtube_id"] = new_youtube_id
        song["channel_title"] = replacement.get("channel_title")
        song["view_count"] = replacement.get("view_count", 0)
        song["duration_seconds"] = replacement.get("duration_seconds", 0)
        song["published_at"] = replacement.get("published_at")
        song["source_query"] = replacement.get("source_query", "replacement_search")
        song["start_time"] = self.generate_start_time(replacement.get("duration_seconds", 180))

        cache = load_metadata_cache()

        if old_youtube_id in cache:
            cached_song = cache.pop(old_youtube_id)
            cached_song.update(song)
            cache[new_youtube_id] = cached_song
        else:
            cache[new_youtube_id] = song.copy()

        save_metadata_cache(cache)
        return True

    def ensure_song_embeddable(self, song, decade):
        youtube_id = song.get("youtube_id")

        if not youtube_id:
            return False

        try:
            if is_video_embeddable(youtube_id):
                return True

            replacement = find_replacement_video_for_song(
                artist=song.get("artist", ""),
                title=song.get("title", ""),
                decade=decade,
                exclude_ids={youtube_id}
            )

            if replacement is None:
                print(
                    "No embeddable replacement found | "
                    f"artist={song.get('artist')} | title={song.get('title')}"
                )
                return False

            replaced = self.replace_song_video(song, replacement)

            if replaced:
                print(
                    "Replaced blocked embed video | "
                    f"old={youtube_id} | new={replacement.get('youtube_id')} | "
                    f"title={song.get('title')} | artist={song.get('artist')}"
                )

            return replaced

        except Exception as e:
            error_text = str(e).lower()

            if "quota" in error_text or "quotaexceeded" in error_text:
                self.youtube_quota_exceeded = True
                print("YouTube quota exceeded while checking embeddable replacement.")
            else:
                print(f"Embeddable replacement failed: {e}")

            return False

    def song_identity(self, song):
        artist = str(song.get("artist", "")).strip().lower()
        title = str(song.get("title", "")).strip().lower()
        year = song.get("year")
        return f"{artist}|{title}|{year}"

    def get_song(self, decade, used_songs, last_artist, used_song_keys=None):
        if decade not in self.cache:
            return None

        used_song_keys = used_song_keys or set()
        self.refill_decade_if_needed(decade, min_count=5)

        available = [
            song for song in self.cache[decade]
            if song.get("youtube_id") not in used_songs
            and song.get("artist") != last_artist
            and song.get("year") is not None
            and song.get("title")
            and song.get("artist")
            and self.song_identity(song) not in used_song_keys
        ]

        if not available:
            available = [
                song for song in self.cache[decade]
                if song.get("youtube_id") not in used_songs
                and song.get("year") is not None
                and song.get("title")
                and song.get("artist")
                and self.song_identity(song) not in used_song_keys
            ]

        if not available:
            return None

        random.shuffle(available)

        for song in available:
            if self.ensure_song_embeddable(song, decade):
                return song

        return None
