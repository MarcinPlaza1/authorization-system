# FastAPI Project

An API project built with FastAPI featuring a full structure, authentication, and authorization.

## Requirements

- Python 3.8+
- FastAPI
- SQLAlchemy
- Pydantic
- Other dependencies listed in `requirements.txt`

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd [project-name]
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and adjust the environment variables:
```bash
cp .env.example .env
```

## Running the Application

To start the development server:

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

## API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Testing

To run the tests:

```bash
pytest
```

## Authors
- Marcin Plaza - Lead Developer
