MAKEFLAGS += --jobs=2
.PHONY: install dev
all: install dev-frontend dev precommit image dev-image

install:
	poetry env use 3.11
	poetry install
	poetry run pre-commit install

dev-frontend: config.yml blanco.db
	poetry run python -m bot.dev_server

dev-backend: config.yml blanco.db
	poetry run python -m bot.api.main

dev: config.yml blanco.db
	poetry run python -m bot.main

precommit:
	poetry run pre-commit run --all-files

image:
	docker buildx build -t blanco-bot .

dev-image: config.yml blanco.db image
	docker run --rm -it \
		-v $(PWD):/opt/app \
		-p 8080:8080 \
		blanco-bot
