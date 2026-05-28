# Breathe ESG Backend

Django REST Framework API for the Breathe ESG Carbon Accounting Platform. This service manages the core data model, ingestion pipeline, emission factor calculations, and multi-tenant isolation.

## Technical Architecture

The backend is built with Django 5.1 and Python 3.12, using a modular app structure:

```
apps/
├── core/           # Base models (TenantModel), mixins, and common utilities
├── organizations/  # Tenant root and organizational settings
├── facilities/     # Physical location mapping (SAP Plant codes, Utility accounts)
├── factors/        # Versioned emission factor library (EPA eGRID, DEFRA, IPCC)
├── ingestion/      # Immutable raw data pipeline (File storage + Row-level JSONB)
├── activities/     # The "Golden Records" - normalized GHG Protocol records
├── audit/          # Purpose-built, append-only audit trail
└── dashboard/      # Aggregated analytics for the frontend
```

## Key Design Principles

1. **Immutable Ingestion**: Source data is never modified. `RawDataRow` stores the exact payload received from SAP, Concur, or Utility portals.
2. **Traceable Calculations**: Every `co2e_kg` value includes a `co2e_calculation_audit` JSONB field documenting the exact factor ID, version, and math used.
3. **Temporal Precision**: Handles non-calendar billing periods (common in utilities) by storing exact dates and providing monthly pro-ration for reporting.
4. **Versioned Factors**: Emission factors are time-bounded (`effective_from`/`effective_to`). Historical data is never silently recalculated with new factors.
5. **Strict Multi-Tenancy**: All data models inherit from `TenantModel`, ensuring strict logical isolation at the query layer.

## Getting Started

### Prerequisites
- Python 3.12
- PostgreSQL
- [uv](https://github.com/astral-sh/uv) (recommended)

### Installation & Setup

```bash
cd server

# 1. Install dependencies using uv
uv sync

# 2. Setup environment variables
# cp .env.example .env (if example exists)
# At minimum, configure:
# DATABASE_URL=postgres://user:password@localhost:5432/breathe_esg
# SECRET_KEY=your-secret-key

# 3. Initialize database
uv run manage.py migrate

# 4. Seed the initial emission factor library
uv run manage.py seed_factors

# 5. Create a superuser for the admin interface
uv run manage.py createsuperuser

# 6. Start the development server
uv run manage.py runserver
```

## API Documentation

The API follows RESTful principles and is versioned under `/api/v1/`.

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/ingestion/` | Multi-part upload for SAP, Utility, or Travel files |
| `GET /api/v1/activities/` | List, filter, and export normalized activity records |
| `POST /api/v1/activities/{id}/approve/` | Move a record from 'Pending' to 'Approved' |
| `GET /api/v1/dashboard/summary/` | Aggregated emissions by scope and period |
| `GET /api/v1/factors/` | Search the active emission factor library |
| `GET /api/v1/audit/` | Access the system-wide audit trail |

## Deployment (Koyeb - No Docker)

This project is configured for easy deployment to **Koyeb** using their native Python Buildpack.

### Configuration Files
- `requirements.txt`: Auto-generated from `uv` for buildpack compatibility.
- `Procfile`: Defines the Gunicorn execution command.
- `runtime.txt`: Specifies Python 3.12.

### Deployment Steps

1. **GitHub**: Push this repository to your GitHub account.
2. **Database**: Create a free PostgreSQL instance on [Neon.tech](https://neon.tech) or [Supabase](https://supabase.com). Copy the `DATABASE_URL`.
3. **Koyeb Console**:
   - Create a new **Web Service**.
   - Select your GitHub repository.
   - **Workind Directory**: Set to `server`.
   - **Build Strategy**: Select **Buildpacks**.
   - **Environment Variables**:
     - `DATABASE_URL`: Your Postgres connection string.
     - `DJANGO_SECRET_KEY`: A long random string.
     - `DEBUG`: `False`
     - `ALLOWED_HOSTS`: `your-app-name.koyeb.app`
   - **Expose Port**: 8000 (Gunicorn is configured for this).

4. **Migrations & Factors**:
   Once deployed, you can use the Koyeb "Console" (CLI or Web) to run:
   ```bash
   python manage.py migrate
   python manage.py seed_factors
   ```

## Development

- **Unit Tests**: Run tests with `uv run manage.py test`.
- **Linting**: We follow PEP8 and use `ruff` for linting and formatting.
- **Migrations**: Always review generated migrations before applying them to production.

## Documentation Reference

For deep dives into the logic:
- [DECISIONS.md](../DECISIONS.md): Why we chose specific formats and methods.
- [MODEL.md](../MODEL.md): Database schema and normalization logic.
- [SOURCES.md](../SOURCES.md): Analysis of SAP, Utility, and Travel data formats.
