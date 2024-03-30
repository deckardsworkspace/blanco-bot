.PHONY: install dev

install:
	poetry env use 3.12
	poetry install

dev-frontend: config.yml blanco.db
	poetry run python dev_server.py

dev: config.yml blanco.db
	poetry run python main.py
