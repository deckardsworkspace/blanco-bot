.PHONY: install dev

install:
	poetry env use 3.12
	poetry install
	poetry run pre-commit install

dev-frontend: config.yml blanco.db
	poetry run python -m bot.dev_server

dev: config.yml blanco.db
	poetry run python -m bot.main

precommit:
	poetry run pre-commit run --all-files
