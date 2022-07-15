from math import floor
from typing import Tuple, Union


def human_readable_time(ms: Union[int, float]) -> Tuple[int, int, int]:
    m, s = divmod(ms / 1000, 60)
    h, m = divmod(m, 60)
    return floor(h), floor(m), floor(s)


def machine_readable_time(colon_delimited_time: str) -> int:
    # Parse colon delimited time (e.g. "1:30:00") into milliseconds
    time_segments = colon_delimited_time.split(':')
    s = int(time_segments[-1])
    m = int(time_segments[-2])
    h = int(time_segments[0]) if len(time_segments) == 3 else 0
    return h * 3600000 + m * 60000 + s * 1000
