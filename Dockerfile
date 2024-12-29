FROM python:3.11-slim

# Ustaw zmienne środowiskowe
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false

# Dodaj poetry do PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Ustaw katalog roboczy
WORKDIR /app

# Zainstaluj zależności systemowe i Poetry
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -sSL https://install.python-poetry.org | python3 -

# Skopiuj pliki konfiguracyjne Poetry
COPY pyproject.toml poetry.lock* ./

# Zainstaluj zależności projektu
RUN poetry install --no-interaction --no-ansi --no-root

# Skopiuj kod aplikacji
COPY . .

# Utwórz użytkownika bez uprawnień roota
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app
USER appuser

# Wystaw port
EXPOSE 8000

# Uruchom aplikację
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 