# Development webserver
from database import Database
from server.main import run_app
from subprocess import run
import asyncio
import sys
import threading


# Thread for spawning the TailwindCSS compiler
def run_tailwind():
    run('tailwindcss -i ./server/static/css/base.css -o ./server/static/css/main.css --watch', shell=True)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f'Usage: python {sys.argv[0]} <path to database>')
        sys.exit(1)
    
    thread = threading.Thread(target=run_tailwind)
    thread.start()

    db = Database(sys.argv[1])
    loop = asyncio.get_event_loop()
    loop.create_task(run_app(db, debug=True))
    loop.run_forever()
