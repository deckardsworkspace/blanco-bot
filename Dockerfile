FROM python:3.11 AS dependencies

# Install build-essential for building Python packages
RUN apt-get update && apt-get install -y build-essential

# Install pip requirements under virtualenv
RUN pip install --upgrade pip
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
COPY requirements.txt .
RUN pip install -r requirements.txt


FROM python:3.11-slim AS main
COPY --from=dependencies /opt/venv /opt/venv
LABEL maintainer="Jared Dantis <jareddantis@gmail.com>"

# Copy bot files and run bot
COPY . /opt/app
WORKDIR /opt/app
ENV PATH="/opt/venv/bin:${PATH}"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python3", "main.py"]
