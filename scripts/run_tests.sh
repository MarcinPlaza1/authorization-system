#!/bin/bash

# Czekaj na dostępność bazy danych
echo "Czekam na dostępność bazy danych..."
sleep 5

# Uruchom migracje
echo "Uruchamianie migracji..."
alembic upgrade head

# Inicjalizacja bazy danych
echo "Inicjalizacja bazy danych..."
python -c "
import asyncio
from app.db.database import init_db

async def init():
    await init_db()

asyncio.run(init())
"

# Uruchom testy z generowaniem raportu pokrycia
echo "Uruchamianie testów..."
pytest tests/unit/ -v \
    --cov=app \
    --cov-report=term-missing \
    --cov-report=html:coverage_html \
    -p no:warnings 