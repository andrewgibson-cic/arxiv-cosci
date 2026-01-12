# Frontend Architecture V2

## Overview

This document describes the new high-performance graph visualization architecture implemented in the ArXiv Co-Scientist frontend.

## Architecture Pattern: "The Hybrid Model"

The application uses a **dual-layer architecture** to handle thousands of nodes efficiently:

### 1. The Engine (WebGL Layer)
- **Technology**: Sigma.js v3 + Graphology
- **Purpose**: Renders 5,000+ nodes at 60 FPS using GPU acceleration
- **Location**: `src/components/Graph/`
- **Pattern**: "Ref Pattern" - Direct imperative integration with React

### 2. The Shell (React Layer)
- **Technology**: React 18 + Zustand
- **Purpose**: Renders the HUD (search, panels, controls) that floats above the canvas
- **Location**: `src/components/HUD/`
- **Pattern**: "State Tunnel" - Events flow from Sigma → Store → UI

## Key Design Decisions

### Why Not Use @react-sigma/core?
The `@react-sigma/core` wrapper adds unnecessary abstraction and performance overhead. We use **direct Sigma.js integration** with `useRef` for maximum control and performance.

### The "Ref Pattern"
```tsx
const sigmaRef = useRef<Sigma | null>(null);

useEffect(() => {
  const sigma = new Sigma(graph, containerRef.current);
  sigmaRef.current = sigma;
  
  sigma.on('clickNode', ({ node }) => {
    // Bridge to React state
    setSelectedNodeId(node);
  });
}, []);
```

### The "State Tunnel"
1. User clicks node in WebGL canvas
2. Sigma fires `clickNode` event
3. Event handler updates Zustand store
4. React components re-render (Inspector slides in)
5. Store triggers imperative graph updates (dim neighbors)

**Critical**: We NEVER re-render the canvas component. Visual updates use `graph.setNodeAttribute()`.

## Directory Structure

```
src/
├── components/
│   ├── Graph/              # THE ENGINE
│   │   ├── GraphCanvas.tsx # Sigma.js integration
│   │   └── Layouts.ts      # ForceAtlas2, Circular
│   │
│   ├── HUD/                # THE SHELL
│   │   ├── Omnibox.tsx     # Search (Cmd+K)
│   │   ├── Inspector.tsx   # Side panel
│   │   └── Controls.tsx    # Zoom, layout toggle
│   │
│   └── shared/             # UI primitives
│       ├── GlassPanel.tsx  # Glassmorphism container
│       └── Button.tsx      # Consistent buttons
│
├── hooks/
│   └── useGraphStore.ts    # Zustand global state
│
└── pages/
    └── GraphViewV2.tsx     # Integrated page
```

## State Management

### Zustand Store (`useGraphStore`)

**Why Zustand?** Zero boilerplate, excellent performance, no Context hell.

```tsx
interface GraphState {
  // Refs (not reactive)
  graphInstance: Graph | null;
  sigmaInstance: Sigma | null;
  
  // UI State
  selectedNodeId: string | null;
  layoutMode: 'force' | 'circular';
  viewMode: 'graph' | 'list';
  
  // Filter State
  visibleCategories: Set<string>;
  yearRange: [number, number] | null;
}
```

## Performance Optimizations

### 1. Imperative Updates
```tsx
// ❌ BAD: Triggers full React re-render
setNodes([...nodes, newNode]);

// ✅ GOOD: Direct graph mutation
graph.addNode(id, attributes);
sigma.refresh();
```

### 2. Layout Workers
ForceAtlas2 runs in animation frames, non-blocking:
```tsx
startAnimatedLayout(graph, (iteration) => {
  console.log(`Layout iteration: ${iteration}`);
});
```

### 3. Event Debouncing
Hover events are debounced to prevent excessive updates.

## Visual Design: Glass Interface

### Theme System
- **Light Mode**: `bg-white/85` + `backdrop-blur-md`
- **Dark Mode**: `bg-slate-900/85` + `backdrop-blur-md`
- **Category Colors**: 
  - Physics: `#3B82F6` (Blue)
  - Math: `#EF4444` (Red)
  - CS: `#10B981` (Green)

### Components
All HUD components use `<GlassPanel>` for consistent glassmorphism effect.

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd+K` / `Ctrl+K` | Open Omnibox |
| `Escape` | Close Omnibox |
| `Arrow Up/Down` | Navigate search results |
| `Enter` | Fly to selected paper |

## Accessibility

### Current Implementation
- Semantic HTML in HUD components
- ARIA labels on interactive elements
- Keyboard navigation in Omnibox

### Planned
- View toggle (Graph ↔ List)
- Screen reader fallback table
- Full keyboard navigation

## Integration with Backend

### API Contract
```tsx
interface CitationNetworkResponse {
  center_paper: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  depth: number;
  total_nodes: number;
  total_edges: number;
}
```

### Data Flow
1. `useQuery` fetches from `/graph/citations/:arxivId`
2. Response stored in Zustand via `setGraphData()`
3. `GraphCanvas` initializes Sigma with data
4. HUD components reactively display info

## Development

### Running Locally
```bash
cd apps/web
npm install
npm run dev
```

### Testing Graph Visualization
Navigate to: `http://localhost:5173/graph/2301.12345`

### Common Pitfalls

1. **Blank Canvas**: Ensure container has explicit height/width
2. **Double Render**: Use `isInitializedRef` to prevent React Strict Mode issues
3. **Memory Leaks**: Always call `sigma.kill()` in cleanup

## Future Enhancements

### Phase 1 (Completed) ✅
- [x] Core architecture
- [x] Omnibox with fly-to
- [x] Inspector panel
- [x] Layout engine

### Phase 2 (Completed) ✅
- [x] Fuzzy search with Fuse.js
- [x] Time slider for year filtering
- [x] Category filter chips
- [x] ViewToggle component (Graph ↔ List)
- [x] ListView with sortable table
- [ ] Edge bundling for dense graphs (deferred to Phase 3)

### Phase 3 (Future)
- [ ] Edge bundling with opacity control
- [ ] WebGPU support (100k+ nodes)
- [ ] Collaborative features
- [ ] Animation timeline playback

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Nodes | 10,000 | ✅ |
| FPS | 60 | ✅ |
| Layout Time | < 3s | ✅ |
| Memory | < 500MB | ✅ |

## References

- [Sigma.js Documentation](https://www.sigmajs.org/)
- [Graphology](https://graphology.github.io/)
- [Frontend Developer Guide](./Frontend%20Developer%20Guide.md)
- [Architecture Diagram](./frontend_architecture)