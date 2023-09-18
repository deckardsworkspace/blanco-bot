ARG RELEASE="0.0.0-unknown"


FROM node:lts-alpine AS tailwind

# Compile Tailwind CSS
RUN mkdir -p /opt/build
COPY tailwind.config.js /opt/build/
COPY server/ /opt/build/server
WORKDIR /opt/build
RUN npm install -D tailwindcss && \
    npx tailwindcss -i ./server/static/css/base.css \
    -o ./server/static/css/main.css --minify


FROM python:3.11 AS dependencies

# Install build-essential for building Python packages
RUN apt-get update && apt-get install -y build-essential

# Install pip requirements under virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
COPY requirements.txt .
RUN pip install --upgrade pip wheel && pip install -r requirements.txt


FROM python:3.11-slim AS main
ARG RELEASE
COPY --from=dependencies /opt/venv /opt/venv
LABEL maintainer="Jared Dantis <jareddantis@gmail.com>"

# Copy bot files
COPY . /opt/app
COPY --from=tailwind /opt/build/server/static/css/main.css /opt/app/server/static/css/main.css
WORKDIR /opt/app

# Set release
RUN sed -i "s/0.0.0-unknown/${RELEASE}/" utils/constants.py

# Run bot
ENV PATH="/opt/venv/bin:${PATH}"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python3", "main.py"]
