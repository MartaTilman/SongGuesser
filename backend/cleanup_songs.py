"""
Run this from the backend folder:
  venv\Scripts\python cleanup_songs.py

Removes songs from Supabase that:
- are private / deleted
- have embedding disabled
- are region-blocked in Croatia (HR)
"""

import json
import os
import sys
import urllib.request
import urllib.error

sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv(".env")

import psycopg

DATABASE_URL = os.getenv("DATABASE_URL")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

USER_COUNTRY = "HR"  # Croatia

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set in .env")
    sys.exit(1)

if not YOUTUBE_API_KEY:
    print("ERROR: YOUTUBE_API_KEY not set in .env")
    sys.exit(1)


def check_videos(youtube_ids):
    results = {}
    for i in range(0, len(youtube_ids), 50):
        batch = youtube_ids[i:i + 50]
        url = (
            "https://www.googleapis.com/youtube/v3/videos"
            f"?part=status,contentDetails&id={','.join(batch)}&key={YOUTUBE_API_KEY}"
        )
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())

        returned_ids = set()
        for item in data.get("items", []):
            vid_id = item["id"]
            returned_ids.add(vid_id)
            status = item.get("status", {})
            region = item.get("contentDetails", {}).get("regionRestriction", {})
            blocked = region.get("blocked", [])
            allowed = region.get("allowed", None)

            blocked_in_hr = (
                USER_COUNTRY in blocked
                or (allowed is not None and USER_COUNTRY not in allowed)
            )

            results[vid_id] = {
                "exists": True,
                "public": status.get("privacyStatus") == "public",
                "embeddable": status.get("embeddable", False),
                "blocked_in_hr": blocked_in_hr,
                "blocked_regions": blocked,
                "allowed_regions": allowed,
            }

        # IDs missing from response = deleted or private
        for vid_id in batch:
            if vid_id not in returned_ids:
                results[vid_id] = {
                    "exists": False,
                    "public": False,
                    "embeddable": False,
                    "blocked_in_hr": False,
                    "blocked_regions": [],
                    "allowed_regions": None,
                }

    return results


with psycopg.connect(DATABASE_URL) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT youtube_id, artist, title FROM song_metadata_cache")
        songs = cur.fetchall()

print(f"Total songs: {len(songs)}")
print(f"Checking YouTube status (country={USER_COUNTRY})...\n")

youtube_ids = [s[0] for s in songs]
video_info = check_videos(youtube_ids)

removable = []

for yt_id, artist, title in songs:
    info = video_info.get(yt_id, {})
    reasons = []

    if not info.get("exists"):
        reasons.append("deleted/private")
    if not info.get("embeddable"):
        reasons.append("embedding disabled")
    if info.get("blocked_in_hr"):
        reasons.append(f"blocked in {USER_COUNTRY}")

    if reasons:
        removable.append((yt_id, artist, title, reasons))
        print(f"  ✗ REMOVE  {artist} - {title}  ({', '.join(reasons)})")
    else:
        print(f"  ✓ OK      {artist} - {title}")

print(f"\nKept:    {len(songs) - len(removable)}")
print(f"Removed: {len(removable)}")

if removable:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM song_metadata_cache WHERE youtube_id = ANY(%s)",
                ([r[0] for r in removable],)
            )
        conn.commit()
    print(f"\n✓ Done — removed {len(removable)} songs from Supabase.")
else:
    print("\n✓ All songs are playable in Croatia, nothing removed.")
