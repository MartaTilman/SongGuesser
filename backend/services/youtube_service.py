import os
import re
import isodate
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


BAD_WORDS = [
    "live",
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
    "fan made",
    "fanmade",
    "version",
    "soul version",
    "lofi",
    "8d audio",
    "remastered",
    "edit"
]

BAD_PHRASES = [
    "greatest hits",
    "best songs",
    "top 10",
    "top 20",
    "top songs",
    "most recognizable songs",
    "old songs collection",
    "non stop",
    "mega hits",
    "all time hits",
    "best of",
    "billboard hits",
    "songs of the",
    "hits of the",
    "decade hits",
    "oldies but goodies"
]

GOOD_CHANNEL_HINTS = [
    "vevo",
    "official",
    "topic",
    "records",
    "music",
    "entertainment"
]

DECADE_TEXT_PATTERNS = {
    "50s": ["1950", "1950s", "50s", "50's"],
    "60s": ["1960", "1960s", "60s", "60's"],
    "70s": ["1970", "1970s", "70s", "70's"],
    "80s": ["1980", "1980s", "80s", "80's"],
    "90s": ["1990", "1990s", "90s", "90's"],
    "2000s": ["2000", "2000s"],
    "2010s": ["2010", "2010s"],
    "2020s": ["2020", "2020s"]
}


def normalize_text(value):
    return str(value or "").strip().lower()


def title_has_bad_words(title):
    lowered = normalize_text(title)

    if any(word in lowered for word in BAD_WORDS):
        return True

    if any(phrase in lowered for phrase in BAD_PHRASES):
        return True

    return False


def channel_quality_score(channel_title):
    lowered = normalize_text(channel_title)
    score = 0

    for hint in GOOD_CHANNEL_HINTS:
        if hint in lowered:
            score += 1

    return score


def looks_like_song_title(title):
    cleaned = normalize_text(title)

    if len(cleaned) < 5:
        return False

    if " - " in cleaned or ":" in cleaned:
        return True

    suspicious_patterns = [
        r"\b\d+\s+songs\b",
        r"\btop\s+\d+\b",
        r"\bbest\s+of\b",
        r"\bcollection\b",
        r"\bplaylist\b",
        r"\bjukebox\b"
    ]

    for pattern in suspicious_patterns:
        if re.search(pattern, cleaned):
            return False

    return True


def is_decade_thematic_fake(title, target_decade):
    """
    Odbacuje videe tipa:
    - '1950's soul version'
    - 'song in 60s style'
    - '80s remix'
    """
    lowered = normalize_text(title)

    target_patterns = DECADE_TEXT_PATTERNS.get(target_decade, [])
    mentions_target_decade = any(pattern in lowered for pattern in target_patterns)

    suspicious_context = [
        "style",
        "version",
        "soul version",
        "in the style of",
        "remix",
        "inspired",
        "type beat"
    ]

    if mentions_target_decade and any(word in lowered for word in suspicious_context):
        return True

    return False


def build_search_queries(decade):
    if decade == "50s":
        return [
            'site:youtube.com 1950s official music video',
            '"1950s" "official video" song',
            '"50s" "official music video"',
            '"rock and roll" official video oldies'
        ]

    if decade == "60s":
        return [
            '"1960s" "official music video"',
            '"60s" "official video" song',
            '"motown" official video',
            '"british invasion" official video'
        ]

    if decade == "70s":
        return [
            '"1970s" official music video',
            '"70s" official song',
            '"disco" official video',
            '"classic rock" official video'
        ]

    if decade == "80s":
        return [
            '"1980s" official music video',
            '"80s" vevo official video',
            '"new wave" official video',
            '"80s pop" official video'
        ]

    if decade == "90s":
        return [
            '"1990s" official music video',
            '"90s" official video',
            '"90s pop" official video',
            '"90s rock" official video'
        ]

    if decade == "2000s":
        return [
            '"2000s" official music video',
            '"2000s hit" official video',
            '"2000s pop" official video',
            '"2000s rock" official video'
        ]

    if decade == "2010s":
        return [
            '"2010s" official music video',
            '"2010s hit" official video',
            '"2010s pop" official video',
            '"2010s song" official video'
        ]

    return [
        '"2020s" official music video',
        '"2020s hit" official video',
        '"2020s pop" official video',
        '"2020s song" official video'
    ]


def search_youtube_candidates(decade, max_results_per_query=15):
    queries = build_search_queries(decade)
    collected = {}

    for query in queries:
        try:
            response = youtube.search().list(
                part="snippet",
                q=query,
                maxResults=max_results_per_query,
                type="video",
                videoCategoryId="10",
                order="viewCount"
            ).execute()
        except Exception as e:
            print(f"YouTube search error for query '{query}': {e}")

            error_text = str(e).lower()
            if "quota" in error_text or "quotaexceeded" in error_text:
                raise RuntimeError("YouTube quota exceeded")

            continue

        for item in response.get("items", []):
            video_id = item["id"]["videoId"]

            if video_id in collected:
                continue

            snippet = item.get("snippet", {})

            collected[video_id] = {
                "youtube_id": video_id,
                "raw_title": snippet.get("title", ""),
                "channel_title": snippet.get("channelTitle", ""),
                "description": snippet.get("description", ""),
                "published_at": snippet.get("publishedAt"),
                "source_query": query
            }

    return list(collected.values())


def fetch_video_details(video_ids):
    if not video_ids:
        return {}

    details = {}

    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]

        try:
            response = youtube.videos().list(
                part="contentDetails,statistics,snippet",
                id=",".join(chunk)
            ).execute()
        except Exception as e:
            print(f"YouTube details error: {e}")

            error_text = str(e).lower()
            if "quota" in error_text or "quotaexceeded" in error_text:
                raise RuntimeError("YouTube quota exceeded")

            continue

        for item in response.get("items", []):
            video_id = item.get("id")
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            content = item.get("contentDetails", {})

            duration_iso = content.get("duration", "PT0S")
            try:
                duration_seconds = int(isodate.parse_duration(duration_iso).total_seconds())
            except Exception:
                duration_seconds = 0

            try:
                view_count = int(stats.get("viewCount", 0))
            except Exception:
                view_count = 0

            details[video_id] = {
                "youtube_id": video_id,
                "channel_title": snippet.get("channelTitle", ""),
                "description": snippet.get("description", ""),
                "published_at": snippet.get("publishedAt"),
                "view_count": view_count,
                "duration_seconds": duration_seconds
            }

    return details


def passes_basic_filters(candidate, decade):
    raw_title = candidate.get("raw_title", "")
    channel_title = candidate.get("channel_title", "")
    duration_seconds = candidate.get("duration_seconds", 0)
    view_count = candidate.get("view_count", 0)

    if not raw_title:
        return False

    if title_has_bad_words(raw_title):
        return False

    if is_decade_thematic_fake(raw_title, decade):
        return False

    if not looks_like_song_title(raw_title):
        return False

    if duration_seconds < 120 or duration_seconds > 480:
        return False

    min_views_by_decade = {
        "50s": 100000,
        "60s": 100000,
        "70s": 150000,
        "80s": 250000,
        "90s": 250000,
        "2000s": 400000,
        "2010s": 500000,
        "2020s": 300000
    }

    if view_count < min_views_by_decade.get(decade, 300000):
        return False

    lowered_title = normalize_text(raw_title)
    lowered_channel = normalize_text(channel_title)

    if "various artists" in lowered_title:
        return False

    if any(x in lowered_title for x in ["top", "best", "hits", "collection"]) and any(
        x in lowered_title for x in DECADE_TEXT_PATTERNS.get(decade, [])
    ):
        return False

    spammy_channel_patterns = ["clips", "tv", "news", "memes"]
    spam_hits = sum(1 for pattern in spammy_channel_patterns if pattern in lowered_channel)
    if spam_hits >= 2:
        return False

    return True


def enrich_candidates_with_details(candidates):
    ids = [candidate["youtube_id"] for candidate in candidates]
    details_map = fetch_video_details(ids)

    enriched = []
    for candidate in candidates:
        merged = {
            **candidate,
            **details_map.get(candidate["youtube_id"], {})
        }
        enriched.append(merged)

    return enriched


def score_candidate(candidate):
    score = 0

    raw_title = candidate.get("raw_title", "")
    channel_title = candidate.get("channel_title", "")
    view_count = candidate.get("view_count", 0)
    duration_seconds = candidate.get("duration_seconds", 0)

    if looks_like_song_title(raw_title):
        score += 20

    if not title_has_bad_words(raw_title):
        score += 25

    channel_score = channel_quality_score(channel_title)
    if channel_score >= 1:
        score += 15
    if channel_score >= 2:
        score += 10

    if 150 <= duration_seconds <= 330:
        score += 10

    if view_count >= 500000:
        score += 10

    if view_count >= 5000000:
        score += 10

    return score


def fetch_youtube_candidates_for_decade(decade, max_results_per_query=15):
    raw_candidates = search_youtube_candidates(decade, max_results_per_query)
    enriched = enrich_candidates_with_details(raw_candidates)

    filtered = []
    for candidate in enriched:
        if passes_basic_filters(candidate, decade):
            candidate["pre_validation_score"] = score_candidate(candidate)
            filtered.append(candidate)

    filtered.sort(
        key=lambda c: (c.get("pre_validation_score", 0), c.get("view_count", 0)),
        reverse=True
    )

    return filtered