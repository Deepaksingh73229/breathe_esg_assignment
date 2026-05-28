# Breathe ESG Frontend

The frontend for the Breathe ESG platform, built with Next.js 15, TypeScript, and TailwindCSS. It provides a modern, intuitive interface for sustainability analysts to manage carbon data ingestion, review calculations, and monitor organizational emissions.

## Features

- **Analyst Dashboard**: Real-time overview of ingestion health, review queue status, and key emission metrics.
- **Ingestion Workflow**: Interactive UI for uploading SAP, Utility, and Travel data, with immediate validation feedback.
- **Review & Audit**: Detailed views for reviewing activity records, inspecting calculation audits, and managing the approval workflow.
- **Facility Management**: Mapping interface for organizational facilities and their associated metadata (SAP plant codes, utility accounts).
- **Factor Browser**: Transparency into the active emission factor library and their regional applicability.

## Tech Stack

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: TailwindCSS
- **Components**: Radix UI (accessible primitives)
- **Charts**: Recharts / Tremor (for emissions visualization)
- **Data Fetching**: Custom hooks wrapping the `services/` layer

## Getting Started

### Installation

Ensure you have `pnpm` installed.

```bash
cd frontend
pnpm install
```

### Development

Run the development server:

```bash
pnpm dev
```

The application will be available at `http://localhost:3000`.

### Configuration

The frontend expects the backend API to be available at `http://localhost:8000/api/v1`. You can configure this in your environment variables if needed.

## Directory Structure

- `app/`: Next.js App Router pages and layouts.
- `components/`: Reusable UI components, categorized by feature.
  - `ui/`: Base design system components.
  - `layout/`: Sidebar, Navigation, Auth Gates.
  - `charts/`: Specialized emissions visualization components.
- `services/`: API client and domain-specific service layers for communicating with the Django backend.
- `types/`: Global TypeScript interfaces and enums.
- `lib/`: Utility functions and shared logic.

## Learn More

To learn more about the project's architectural decisions, check the documentation in the root directory:
- [DECISIONS.md](../DECISIONS.md)
- [MODEL.md](../MODEL.md)
- [TRADEOFFS.md](../TRADEOFFS.md)
