ARG RELEASE="0.0.0-unknown"


FROM --platform=$BUILDPLATFORM python:3.11 AS dependencies
ARG TARGETARCH

# Install build-essential for building Python packages
RUN apt-get update && apt-get install -y build-essential curl

# Install Poetry
RUN pip install poetry==1.8.2
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Copy files
WORKDIR /app
COPY pyproject.toml poetry.lock tailwind.config.js dashboard/static/css/base.css ./

# Install dependencies
RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --without dev

# Compile Tailwind CSS
RUN echo "Downloading Tailwind CLI for ${TARGETARCH}" && \
    if [ "${TARGETARCH}" = "amd64" ]; then \
      curl -sL https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64 -o ./tailwindcss; \
    else \
      curl -sL https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-${TARGETARCH} -o ./tailwindcss; \
    fi && \
    chmod +x ./tailwindcss && \
    ./tailwindcss -i ./base.css -o ./main.css --minify


FROM python:3.11-slim AS main
ARG RELEASE
LABEL maintainer="Jared Dantis <jareddantis@gmail.com>"

# Copy bot files
COPY . /opt/app
COPY --from=dependencies /app/.venv /opt/venv
COPY --from=dependencies /app/main.css /opt/app/dashboard/static/css/main.css
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
