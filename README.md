# Expense Tracker API

A small REST API for keeping track of personal expenses. Each user registers, logs in, creates their own categories and logs expenses against them. Everything is private to the account: nobody can see or touch anyone else's data.

I built it to practice the things a real Django backend needs beyond the tutorial level: token authentication, per-user data isolation, filtering and search, aggregation queries, automated tests, a PostgreSQL setup that runs with one command, and CI.

## What it does

- Registration, login and logout with token authentication
- Categories (unique per user, case-insensitive)
- Expenses with amount, description, date and an optional category
- Filtering by category, date range and amount range
- Search over descriptions and category names, ordering, pagination
- A summary endpoint that returns the total, the number of expenses and a breakdown per category for whatever filters you pass in
- Django admin for inspecting data
- 39 tests, running on PostgreSQL in GitHub Actions

## Stack

Python 3.12, Django 6.1, Django REST Framework, django-filter, PostgreSQL 16, gunicorn, WhiteNoise, Docker Compose.

## Running it with Docker

You need Docker with the Compose plugin.

```bash
git clone https://github.com/fgxdu00/expense-tracker-api.git
cd expense-tracker-api
cp .env.example .env
```

Open `.env` and change `SECRET_KEY` and `POSTGRES_PASSWORD`. Then:

```bash
docker compose up --build
```

The API is now available at `http://localhost:8000/api/`. Migrations are applied automatically when the web container starts.

To use the admin site, create a superuser:

```bash
docker compose exec web python manage.py createsuperuser
```

The admin lives at `http://localhost:8000/admin/`.

## Running it locally without Docker

If you do not set any `POSTGRES_*` variables the project falls back to a local SQLite file, which is handy for quick experiments.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DEBUG=1
python manage.py migrate
python manage.py runserver
```

To run against your own PostgreSQL instead, export `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` and `POSTGRES_PORT` before the commands above.

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `SECRET_KEY` | Django secret key, required unless `DEBUG=1` | none |
| `DEBUG` | Set to `1` for development | `0` |
| `ALLOWED_HOSTS` | Comma separated list of hosts | `localhost,127.0.0.1` |
| `TIME_ZONE` | Time zone used for default dates | `UTC` |
| `POSTGRES_DB` | Database name, enables PostgreSQL when set | none |
| `POSTGRES_USER` | Database user | `postgres` |
| `POSTGRES_PASSWORD` | Database password | empty |
| `POSTGRES_HOST` | Database host | `localhost` |
| `POSTGRES_PORT` | Database port | `5432` |

## API

All endpoints except registration and login need the header `Authorization: Token <your token>`. Lists are paginated, 20 items per page, use `?page=2` for the next one.

| Method | Endpoint | Description |
| --- | --- | --- |
| POST | `/api/auth/register/` | Create an account, returns a token |
| POST | `/api/auth/login/` | Exchange username and password for a token |
| POST | `/api/auth/logout/` | Delete the current token |
| GET | `/api/auth/me/` | Current user |
| GET, POST | `/api/categories/` | List or create categories |
| GET, PUT, PATCH, DELETE | `/api/categories/{id}/` | Work with one category |
| GET, POST | `/api/expenses/` | List or create expenses |
| GET, PUT, PATCH, DELETE | `/api/expenses/{id}/` | Work with one expense |
| GET | `/api/expenses/summary/` | Totals and per-category breakdown |

### Expense list parameters

| Parameter | Example | Meaning |
| --- | --- | --- |
| `category` | `?category=3` | Only expenses in this category |
| `date_from`, `date_to` | `?date_from=2026-02-01&date_to=2026-02-28` | Inclusive date range |
| `min_amount`, `max_amount` | `?min_amount=10&max_amount=50` | Inclusive amount range |
| `search` | `?search=bus` | Matches description and category name |
| `ordering` | `?ordering=-amount` | One of `date`, `amount`, `created_at`, prefix with `-` to reverse |

The summary endpoint accepts the same parameters, so `?date_from=2026-02-01&date_to=2026-02-28` gives you February.

### Example session

Register and keep the token:

```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "email": "demo@example.com", "password": "correct-horse-battery"}'
```

Create a category:

```bash
curl -X POST http://localhost:8000/api/categories/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Food"}'
```

Add an expense to it:

```bash
curl -X POST http://localhost:8000/api/expenses/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": "12.50", "description": "Lunch", "date": "2026-03-10", "category": 1}'
```

Ask for a summary:

```bash
curl "http://localhost:8000/api/expenses/summary/?date_from=2026-03-01" \
  -H "Authorization: Token YOUR_TOKEN"
```

Response:

```json
{
  "total": "12.50",
  "count": 1,
  "by_category": [
    {"category": 1, "name": "Food", "total": "12.50", "count": 1}
  ]
}
```

Expenses without a category show up as `Uncategorized` in the breakdown.

## Tests

```bash
python manage.py test
```

The suite covers registration and login rules, data isolation between users, validation of amounts and categories, every filter, search, ordering, pagination and the summary maths. GitHub Actions runs it against a real PostgreSQL service on every push and pull request, together with `manage.py check` and a check that no model change is missing a migration.

## Project layout

```
config/            project settings, urls, wsgi and asgi entry points
tracker/           the app
  models.py        Category and Expense
  serializers.py   validation, including per-user category checks
  filters.py       expense filters
  views.py         auth views and the two viewsets
  urls.py          routes
  tests/           test suite
Dockerfile         production-style image with gunicorn
docker-compose.yml web and PostgreSQL
```

## Some decisions worth mentioning

- Querysets are always filtered by the logged-in user, so another user's object returns 404 instead of 403 and its existence is not leaked.
- The category field on an expense only accepts the current user's categories, and the category filter is limited the same way.
- Deleting a category keeps its expenses and turns them into uncategorized ones.
- Amounts are stored as decimals with two places and must be at least 0.01. Money never goes through floats.
- The summary reuses the list filters, which keeps the two endpoints consistent without duplicating logic.

## Ideas for later

- Monthly budgets with a warning when a category goes over
- CSV export
- Recurring expenses
- Token expiry or JWT

## License

MIT, see `LICENSE`.
