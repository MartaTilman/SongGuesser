import random
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from services.song_parser import parse_song_from_title
from services.song_year_service import get_song_year, year_to_decade
from services.metadata_cache import load_metadata_cache, save_metadata_cache

load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def fetch_songs_for_decade(decade):

    metadata_cache = load_metadata_cache()

    queries = [
        f"official music video {decade}",
        f"{decade} hit song official video",
        f"top song {decade} official video"
    ]

    songs = []
    seen_videos = set()

    for query in queries:

        request = youtube.search().list(
            part="snippet",
            q=query,
            maxResults=15,
            type="video",
            videoCategoryId="10",
            order="viewCount"
        )

        response = request.execute()

        for video in response["items"]:

            video_id = video["id"]["videoId"]

            if video_id in seen_videos:
                continue

            seen_videos.add(video_id)

            title = video["snippet"]["title"]

            
            bad_words = [
                "live",
                "cover",
                "karaoke",
                "remix",
                "reaction",
                "tribute",
                "concert"
            ]

            if any(word in title.lower() for word in bad_words):
                continue

            
            if video_id in metadata_cache:

                cached_song = metadata_cache[video_id]

                if cached_song["decade"] == decade:
                    songs.append(cached_song)

                continue

            parsed = parse_song_from_title(title)

            artist = parsed["artist"]
            song_title = parsed["title"]

            year = get_song_year(artist, song_title)
            real_decade = year_to_decade(year)

            if real_decade != decade:
                continue

            start_time = random.randint(25, 70)

            song = {
                "artist": artist,
                "title": song_title,
                "youtube_id": video_id,
                "start_time": start_time,
                "decade": real_decade,
                "year": year
            }

            songs.append(song)

            metadata_cache[video_id] = song

    save_metadata_cache(metadata_cache)

    unique = {}
    for song in songs:
        unique[song["youtube_id"]] = song

    return list(unique.values())