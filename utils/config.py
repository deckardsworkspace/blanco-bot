from typing import List
from yaml import safe_load


# Parse config file
config = {}
with open('config.yml') as f:
    try:
        config = safe_load(f)
    except Exception as e:
        raise ValueError(f'Error parsing config.yml: {e}')


def get_debug_guilds() -> List[int]:
    try:
        return config['bot']['debug']['guild_ids']
    except KeyError:
        return []
