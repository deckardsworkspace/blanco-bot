"""
Main module for the API server.
"""

from asyncio import set_event_loop
from contextlib import asynccontextmanager
from logging import INFO
from typing import TYPE_CHECKING, Any, Optional

from fastapi import FastAPI
from uvicorn import Config, Server, run
from uvicorn.config import LOGGING_CONFIG

from bot.database import Database
from bot.utils.config import config as bot_config
from bot.utils.logger import DATE_FMT_STR, LOG_FMT_COLOR, create_logger

from .routes.account import account_router
from .routes.callback import callback_router
from .utils.session import SessionManager

if TYPE_CHECKING:
  from asyncio import AbstractEventLoop


_database: Optional[Database] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
  logger = create_logger('api.lifespan')

  if _database is None:
    logger.warn('Manually creating database connection')
    database = Database(bot_config.db_file)
  else:
    logger.info('Connecting to database from FastAPI')
    database = _database

  app.state.database = database
  app.state.session_manager = SessionManager(database)
  yield


app = FastAPI(lifespan=lifespan)
app.include_router(account_router)
app.include_router(callback_router)


@app.get('/')
async def health_check():
  return {'status': 'ok'}


def _get_log_config() -> dict[str, Any]:
  log_config = LOGGING_CONFIG
  log_config['formatters']['default']['fmt'] = LOG_FMT_COLOR[INFO]
  log_config['formatters']['default']['datefmt'] = DATE_FMT_STR
  log_config['formatters']['access']['fmt'] = LOG_FMT_COLOR[INFO]

  return log_config


def run_app(loop: 'AbstractEventLoop', db: Database):
  """
  Run the API server in the bot's event loop.
  """
  global _database  # noqa: PLW0603
  _database = db

  set_event_loop(loop)

  config = Config(
    app=app,
    loop=loop,  # type: ignore
    host='0.0.0.0',
    port=bot_config.server_port,
    log_config=_get_log_config(),
  )
  server = Server(config)

  loop.create_task(server.serve())


if __name__ == '__main__':
  run(
    app='bot.api.main:app',
    host='127.0.0.1',
    port=bot_config.server_port,
    reload=True,
    reload_dirs=['bot/api'],
    log_config=_get_log_config(),
  )
