from dataclass.youtube import YouTubeResult
from typing import Dict, List, Tuple
from youtubesearchpython import Playlist, Video, VideosSearch
from .exceptions import YouTubeInvalidURLError
from .string import machine_readable_time


def parse_result(result: Dict) -> YouTubeResult:
    duration = 0
    if 'duration' in result.keys() and result['duration'] is not None:
        duration = machine_readable_time(result['duration'])
    return YouTubeResult(
        title=result['title'],
        author=result['channel']['name'],
        duration_ms=duration,
        url=f'https://www.youtube.com/watch?v={result["id"]}'
    )


def get_youtube_playlist_info(playlist_id: str) -> Tuple[str, str, int]:
    playlist_info = Playlist.getInfo(f'http://youtube.com/playlist?list={playlist_id}')
    return playlist_info['title'], playlist_info['channel']['name'], int(playlist_info['videoCount'])


def get_youtube_playlist_tracks(playlist_id: str) -> Tuple[List[YouTubeResult]]:
    playlist = Playlist(f'http://youtube.com/playlist?list={playlist_id}')
    while playlist.hasMoreVideos:
        playlist.getNextVideos()
    return [parse_result(i) for i in playlist.videos]


def get_youtube_video(video_id: str) -> YouTubeResult:
    try:
        video = Video.get(video_id)
    except:
        raise YouTubeInvalidURLError(video_id)
    else:
        return parse_result(video)


def get_youtube_matches(query: str, desired_duration_ms: int = 0, num_results: int = 10, automatic: bool = True) -> List[YouTubeResult]:
    results: List[YouTubeResult] = []
    blacklist = ('karaoke', 'live', 'instrumental', 'piano', 'cover', 'minus one', 'reverb', 'slowed', 'remix', 'mashup')
    search = VideosSearch(query, limit=num_results)
    search_results = search.result()
    if 'result' in search_results.keys():
        for result in search_results['result']:
            if 'duration' not in result.keys() or result['duration'] is None:
                # Can't play a track with no duration
                continue

            # Skip karaoke, live, instrumental etc versions
            # if the original query did not ask for it
            valid = True
            if automatic:
                for word in blacklist:
                    if word in result['title'].lower() and not word in query.lower():
                        valid = False
                        break

            if valid:
                results.append(parse_result(result))

    if desired_duration_ms > 0:
        if abs(results[0].duration_ms - desired_duration_ms) < 3500:
            # First result is within acceptable range of desired duration,
            # so we just need to sort the elements after the first one.
            saved_result = results[0]
            results = sorted(results[1:], key=lambda x: abs(x.duration_ms - desired_duration_ms))
            results.insert(0, saved_result)
        else:
            # First result is outside acceptable range, so we sort everything
            # results by distance to desired duration.
            results.sort(key=lambda x: abs(x.duration_ms - desired_duration_ms))
    return results
