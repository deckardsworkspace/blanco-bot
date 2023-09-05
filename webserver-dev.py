# Development webserver
from database import Database
from utils.config import config
from server.main import run_app
from subprocess import run
import asyncio
import threading


# Thread for spawning the TailwindCSS compiler
def run_tailwind():
    run('tailwindcss -i ./server/static/css/base.css -o ./server/static/css/main.css --watch', shell=True)


if __name__ == '__main__':
    thread = threading.Thread(target=run_tailwind)
    thread.start()

    db = Database(config.db_file)
    loop = asyncio.get_event_loop()
    loop.create_task(run_app(db, config))
    loop.run_forever()
