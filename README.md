# Breathe ESG Carbon Accounting Platform

Breathe ESG is a comprehensive enterprise platform for carbon accounting, data ingestion, and sustainability reporting. It enables organizations to automate the collection of emissions data from diverse sources like SAP ERP, utility portals, and corporate travel systems, transforming raw data into auditable GHG (Greenhouse Gas) Protocol-compliant records.

## Project Structure

This is a monorepo containing both the frontend and backend components:

- `frontend/`: Next.js application (TypeScript, TailwindCSS) providing the analyst dashboard, ingestion workflow, and audit views.
- `server/`: Django REST Framework (DRF) backend (Python 3.12) handling data normalization, emission factor management, and the core calculation engine.

## Key Features

- **Automated Ingestion**: Support for SAP Fuel & Procurement exports (CSV), Utility Electricity portals (Green Button CSV), and Corporate Travel (Concur/Navan JSON).
- **Audit-Ready Calculations**: Every emission record is fully traceable to its source data and the specific version of the emission factor used.
- **Factor Versioning**: Managed library of emission factors (EPA eGRID, DEFRA, IPCC) with effective dating and regional mapping.
- **Compliance Workflow**: Built-in review and approval process for all ingested data, with immutable audit logs.
- **Multi-Tenancy**: Built from the ground up to support multiple organizations with strict data isolation.

## Technical Stack

### Frontend
- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: TailwindCSS
- **State Management**: React Hooks & Context
- **Data Fetching**: Custom API client for DRF

### Backend
- **Framework**: Django 5.1 & Django REST Framework
- **Language**: Python 3.12
- **Package Manager**: `uv`
- **Database**: PostgreSQL (with JSONB support for audit trails)
- **Task Queue**: Scheduled tasks for factor updates (future)

## Documentation

Comprehensive documentation of the project's design and logic:

- [DECISIONS.md](./DECISIONS.md): Architectural decisions and real-world format choices.
- [MODEL.md](./MODEL.md): Detailed explanation of the data model and normalization logic.
- [SOURCES.md](./SOURCES.md): Deep dive into the data sources (SAP, Utility, Travel) and parsing logic.
- [TRADEOFFS.md](./TRADEOFFS.md): Explanations of what was built, what was not, and why.

## Getting Started

### Prerequisites
- Node.js (v20+)
- Python (v3.12+)
- PostgreSQL
- `uv` (recommended for Python package management)

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd breathe-esg
   ```

2. **Setup Backend**
   ```bash
   cd server
   uv sync
   # Set up .env based on server/README.md
   python manage.py migrate
   python manage.py seed_factors
   python manage.py runserver
   ```

3. **Setup Frontend**
   ```bash
   cd frontend
   pnpm install
   pnpm dev
   ```

Visit `http://localhost:3000` to access the application.
