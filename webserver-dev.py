# Development webserver
from database import Database
from server.main import run_app
import asyncio
import sys


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f'Usage: python {sys.argv[0]} <path to database>')
        sys.exit(1)
    
    db = Database(sys.argv[1])
    loop = asyncio.get_event_loop()
    loop.create_task(run_app(db, debug=True))
    loop.run_forever()
