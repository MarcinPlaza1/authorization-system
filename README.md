# FastAPI Project

Projekt API zbudowany przy użyciu FastAPI z pełną strukturą, uwierzytelnianiem i autoryzacją.

## Wymagania

- Python 3.8+
- FastAPI
- SQLAlchemy
- Pydantic
- oraz inne zależności wymienione w `requirements.txt`

## Instalacja

1. Sklonuj repozytorium:
```bash
git clone [url-repozytorium]
cd [nazwa-projektu]
```

2. Utwórz i aktywuj wirtualne środowisko:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# lub
.\venv\Scripts\activate  # Windows
```

3. Zainstaluj zależności:
```bash
pip install -r requirements.txt
```

4. Skopiuj `.env.example` do `.env` i dostosuj zmienne środowiskowe:
```bash
cp .env.example .env
```

## Uruchomienie

Aby uruchomić serwer deweloperski:

```bash
uvicorn main:app --reload
```

API będzie dostępne pod adresem `http://localhost:8000`

## Dokumentacja API

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Testy

Aby uruchomić testy:

```bash
pytest
```

## Struktura Projektu

```
/project-root
  /app
    /models      - Modele SQLAlchemy
    /routes      - Endpointy API
    /services    - Logika biznesowa
    /db          - Konfiguracja bazy danych
  /tests         - Testy
  /docs          - Dokumentacja
  main.py        - Punkt wejścia aplikacji
  requirements.txt
  README.md
  Dockerfile
  .env
``` 