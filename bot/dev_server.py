"""
This file is used to run the webserver without running the bot,
along with spawning the TailwindCSS compiler. This is useful for
development, as it allows you to see changes to the webserver
without having to restart the bot.
"""

import asyncio
import threading
from subprocess import run

from bot.database import Database
from bot.server.main import run_app
from bot.utils.config import config


def run_tailwind():
  """
  Run the TailwindCSS compiler.
  """
  run(
    ' '.join(
      [
        'tailwindcss',
        '-i',
        './dashboard/static/css/base.css',
        '-o',
        './dashboard/static/css/main.css',
        '--watch',
      ]
    ),
    check=False,
    shell=True,
  )


if __name__ == '__main__':
  thread = threading.Thread(target=run_tailwind)
  thread.start()

  db = Database(config.db_file)
  loop = asyncio.new_event_loop()
  loop.create_task(run_app(db, config))
  loop.run_forever()
