from pytubefix import Search

def suggest_youtube_videos(query: str):
    results = Search(query)
    video_choices = list()

    for video in results.videos:
        watchid = video.watch_url.replace('https://youtube.com/watch?v=', '')
        video_choices.append({
            'title': video.title,
            'watch_url': watchid,
            'length': video.length,
            'thumbnail': video.thumbnail_url,
            'author': video.author,
        })
    return video_choices

