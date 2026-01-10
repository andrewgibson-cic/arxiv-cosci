# ArXiv Co-Scientist Web Frontend

React + TypeScript + Vite frontend for the ArXiv Co-Scientist project.

## Features

- **Search Interface**: Semantic and hybrid search for papers
- **Paper Details**: Full paper information with citations/references
- **Graph Visualization**: Interactive citation networks using Sigma.js
- **Predictions View**: ML-generated link predictions and hypotheses

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **React Router** - Routing
- **TanStack Query** - Server state management
- **Axios** - HTTP client
- **Sigma.js** - Graph visualization
- **Lucide React** - Icons

## Getting Started

### Install Dependencies

```bash
cd apps/web
npm install
```

### Run Development Server

```bash
npm run dev
```

The app will be available at http://localhost:5173

### Build for Production

```bash
npm run build
npm run preview
```

## Project Structure

```
apps/web/
├── src/
│   ├── api/            # API client and types
│   ├── components/     # Reusable components
│   ├── pages/          # Page components
│   ├── hooks/          # Custom React hooks
│   ├── types/          # TypeScript types
│   ├── App.tsx         # Root component
│   ├── main.tsx        # Entry point
│   └── index.css       # Global styles
├── public/             # Static assets
├── index.html          # HTML template
├── vite.config.ts      # Vite configuration
├── tsconfig.json       # TypeScript configuration
└── package.json        # Dependencies
```

## API Integration

The frontend communicates with the FastAPI backend at `http://localhost:8000`.

Vite proxy configuration automatically forwards `/api/*` requests to the backend.

## Development

### Environment Variables

Create `.env.local` for local configuration:

```bash
VITE_API_URL=http://localhost:8000
```

### Code Style

- ESLint for linting
- TypeScript strict mode enabled
- React hooks linting enabled

## Routes

- `/` - Home page
- `/search` - Search interface
- `/paper/:arxivId` - Paper detail page
- `/graph/:arxivId?` - Citation network visualization

## Next Steps

To complete the frontend implementation:

1. Create API client (`src/api/client.ts`)
2. Define TypeScript types (`src/types/`)
3. Build Layout component (`src/components/Layout.tsx`)
4. Build page components (`src/pages/`)
5. Implement Sigma.js graph visualization
6. Add tests