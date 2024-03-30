ARG RELEASE="0.0.0-unknown"


FROM node:lts-alpine AS tailwind

# Compile Tailwind CSS
RUN mkdir -p /opt/build
COPY tailwind.config.js /opt/build/
COPY dashboard/ /opt/build/dashboard
WORKDIR /opt/build
RUN npm install -D tailwindcss && \
    npx tailwindcss -i ./dashboard/static/css/base.css \
    -o ./dashboard/static/css/main.css --minify


FROM python:3.12 AS dependencies

# Install build-essential for building Python packages
RUN apt-get update && apt-get install -y build-essential

# Install Poetry
RUN pip install poetry==1.8.2
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Install dependencies
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --without dev
RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry add setuptools


FROM python:3.12-slim AS main
ARG RELEASE
LABEL maintainer="Jared Dantis <jareddantis@gmail.com>"

# Copy bot files
COPY . /opt/app
COPY --from=dependencies /app/.venv /opt/venv
COPY --from=tailwind /opt/build/dashboard/static/css/main.css /opt/app/dashboard/static/css/main.css
WORKDIR /opt/app

# Set release
RUN sed -i "s/0.0.0-unknown/${RELEASE}/" bot/utils/constants.py

# Run bot
ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
EXPOSE 8080
ENTRYPOINT ["python"]
CMD ["-m", "bot.main"]
