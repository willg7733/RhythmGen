from pytubefix import Search
from pytubefix.exceptions import LiveStreamError


def _is_live_video(video) -> bool:
    live_status = getattr(video, "live_status", None)
    if isinstance(live_status, str) and live_status.lower() == "is_live":
        return True
    return bool(getattr(video, "is_live", False)) or bool(getattr(video, "is_live_stream", False))


def suggest_youtube_videos(query: str):
    results = Search(query)
    video_choices = []

    for video in results.videos:
        try:
            if _is_live_video(video):
                continue

            watch_url = getattr(video, "watch_url", "")
            if not watch_url:
                continue

            video_length = getattr(video, "length", None)
            if video_length is None:
                continue

            watchid = watch_url.replace("https://youtube.com/watch?v=", "")
            video_choices.append({
                "title": getattr(video, "title", "Unknown Title"),
                "watch_url": watchid,
                "length": video_length,
                "thumbnail": getattr(video, "thumbnail_url", ""),
                "author": getattr(video, "author", "Unknown"),
            })
        except LiveStreamError:
            continue
        except Exception:
            continue

    return video_choices

