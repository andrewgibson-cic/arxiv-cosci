# **ArXiv Co-Scientist: Frontend Developer Guide**

## **1\. Executive Summary & Architecture**

The **ArXiv Co-Scientist Frontend** (apps/web) is a high-performance visual intelligence platform designed to navigate thousands of interconnected research papers.

Unlike standard React dashboards, this application faces a unique engineering challenge: **The "Hairball" Problem**. Rendering 5,000+ nodes (papers) and 20,000+ edges (citations) using standard DOM elements (HTML/SVG) would freeze the browser.

Therefore, we utilize a **Hybrid Architecture**:

1. **The Engine (WebGL)**: We use **Sigma.js** (backed by Graphology) to render the graph topology on an HTML \<canvas\> using the GPU. This handles the heavy lifting.  
2. **The Shell (React)**: We use **React 18** to render the "Heads-Up Display" (HUD)—the search bars, side panels, and controls that float *above* the canvas.

**Core Principle**: The Graph Canvas and the React UI are separate worlds. They communicate via a strict "State Tunnel" pattern to ensure performance.

## **2\. Technology Stack**

| Component | Technology | Role |
| :---- | :---- | :---- |
| **Framework** | React 18 \+ TypeScript | Component lifecycle, state management, and UI rendering. |
| **Build Tool** | Vite | Fast HMR and building. |
| **Graph Engine** | **Sigma.js** (WebGL) | Rendering 10k+ nodes at 60FPS. |
| **Data Model** | **Graphology** | A standard library for manipulating graph data structures (independent of rendering). |
| **Styling** | Tailwind CSS | Rapid UI development for the React overlay. |
| **Icons** | Lucide React | Consistent iconography. |

## **3\. Directory Structure**

We strictly separate **Graph Logic** (WebGL/Canvas interactions) from **UI Components** (React DOM elements).

apps/web/src/  
├── components/  
│   ├── Graph/              \# THE ENGINE  
│   │   ├── GraphCanvas.tsx \# The React wrapper for Sigma.js  
│   │   ├── GraphEvents.ts  \# Event listeners (click, hover)  
│   │   └── Layouts.ts      \# ForceAtlas2 / Circular layout logic  
│   │  
│   ├── HUD/                \# THE SHELL (UI Overlays)  
│   │   ├── Omnibox.tsx     \# Main search bar  
│   │   ├── Inspector.tsx   \# Side panel for node details  
│   │   ├── TimeBar.tsx     \# Timeline filter  
│   │   └── Controls.tsx    \# Zoom/Layout toggles  
│   │  
│   └── shared/             \# Generic UI (Buttons, Cards, Modals)  
│  
├── hooks/  
│   ├── useGraphStore.ts    \# Global state (Zustand/Context)  
│   └── useGraphSearch.ts   \# Logic for fuzzy searching nodes  
│  
├── services/  
│   ├── api.ts              \# Axios instances for FastAPI backend  
│   └── graphBuilder.ts     \# Transforms API JSON \-\> Graphology object  
│  
└── types/                  \# TypeScript definitions for Node/Edge data

## **4\. Key Implementation Patterns**

### **A. The "Ref Pattern" (Integration Strategy)**

React's Virtual DOM cannot handle the frequency of updates required for the graph layout. We use a useRef to hold the container, and initialize Sigma.js imperatively inside a useEffect.

// components/Graph/GraphCanvas.tsx  
import { useEffect, useRef } from "react";  
import Graph from "graphology";  
import Sigma from "sigma";

export const GraphCanvas \= ({ data, onNodeClick }) \=\> {  
  const containerRef \= useRef\<HTMLDivElement\>(null);  
  const sigmaRef \= useRef\<Sigma | null\>(null);

  useEffect(() \=\> {  
    // 1\. Initialize Data Model (Graphology)  
    const graph \= new Graph();  
    graph.import(data); 

    // 2\. Initialize Renderer (Sigma)  
    // We attach strictly to the DOM element, bypassing React VDOM  
    if (containerRef.current) {  
      sigmaRef.current \= new Sigma(graph, containerRef.current, {  
        allowInvalidContainer: true,  
        renderEdgeLabels: false, // Performance optim  
      });

      // 3\. Event Binding (The "Bridge" to React)  
      sigmaRef.current.on("clickNode", (event) \=\> {  
        // Pass the raw node ID back to React land  
        onNodeClick(event.node);   
      });  
    }

    // Cleanup  
    return () \=\> sigmaRef.current?.kill();  
  }, \[data, onNodeClick\]);

  return \<div ref={containerRef} style={{ width: "100%", height: "100vh" }} /\>;  
};

### **B. The "State Tunnel" (Interaction Model)**

When a user interacts with the graph, we must sync the visual state without re-rendering the entire canvas.

1. **User Action**: User clicks a node in WebGL.  
2. **Sigma Event**: clickNode fires.  
3. **React State Update**: We set selectedNodeId in a React state/store.  
4. **UI Reacts**: The **Inspector Panel** slides in (React render).  
5. **Graph Reacts**: We imperatively update the graph colors (e.g., dim non-neighbors) using graph.setNodeAttribute.

**Do NOT** trigger a full React re-render of \<GraphCanvas /\> just to change a node's color. Use the graph instance methods directly.

## **5\. UI/UX Strategy: "Shneiderman’s Mantra"**

The interface follows the standard visualization pipeline: *"Overview first, zoom and filter, then details-on-demand."*

### **1\. Overview (The "Hairball" Management)**

* **Initial View**: Force-directed layout (ForceAtlas2) to show clusters.  
* **Visual Encodings**:  
  * **Node Size**: Pagerank / Citation Count (Importance).  
  * **Node Color**: Research Category (e.g., Quantum Physics \= Blue, Topology \= Red).  
  * **Edge Thickness**: Citation strength or similarity score.

### **2\. Zoom & Filter (The Controls)**

* **Omnibox**: A global search bar (cmd+k style). Selecting a result triggers a camera "fly-to" animation.  
* **Faceted Search**: Sidebar controls to filter by Year (Slider) or Category (Checkboxes).  
  * *Implementation Note*: Filtering should just graph.hide() nodes, not remove them from memory, to allow instant undo.

### **3\. Details-on-Demand (The Inspector)**

* **Behavior**: When a node is clicked, the **Inspector Panel** opens on the right.  
* **Content**: Displays the Abstract, Authors, and a list of Citations.  
* **Action**: "Find Gaps" button triggers the API to analyze this specific paper against its neighbors.

## **6\. Developing Locally**

### **Prerequisites**

* Node.js 20+  
* The API server running on port 8000 (see backend README)

### **Setup**

cd apps/web  
npm install

### **Running**

\# Start the dev server  
npm run dev

The app will be available at http://localhost:5173.

### **Common Pitfalls**

1. **"The graph is blank\!"**: Check if the container \<div\> has a defined height/width (CSS). Sigma requires explicit dimensions.  
2. **Performance drops**: Ensure you aren't console logging inside the render loop or mouse move events.  
3. **React strict mode**: Sigma might initialize twice in Strict Mode. Use a ref flag (isInitialized) to prevent double-rendering during dev.

## **7\. Visual System & Component Library**

To maintain performance while ensuring accessibility and beauty, we use a "Glass Interface" pattern where UI elements float above the WebGL canvas.

### **Design Tokens (Tailwind)**

We extend the default Tailwind palette to support high-contrast data visualization in both light and dark modes.

// tailwind.config.js  
module.exports \= {  
  theme: {  
    extend: {  
      colors: {  
        // Science-focused palette  
        physics: '\#3B82F6', // Blue-500  
        math: '\#EF4444',    // Red-500  
        cs: '\#10B981',      // Emerald-500  
          
        // UI Layers  
        glass: {  
          light: 'rgba(255, 255, 255, 0.85)',  
          dark: 'rgba(15, 23, 42, 0.85)',  
        },  
      },  
      backdropBlur: {  
        xs: '2px',  
      }  
    }  
  }  
}

### **Core UI Components**

#### **1\. The Glass Panel**

The container for the Inspector and Control panels. It uses a backdrop blur to ensure text readability without obscuring the graph context behind it.

// components/shared/GlassPanel.tsx  
export const GlassPanel \= ({ children, className }) \=\> (  
  \<div className={\`  
    bg-glass-light dark:bg-glass-dark   
    backdrop-blur-md   
    border border-slate-200 dark:border-slate-700   
    shadow-xl rounded-xl   
    transition-all duration-300  
    ${className}  
  \`}\>  
    {children}  
  \</div\>  
);

#### **2\. The Omnibox (Search)**

A floating command palette. Crucial for "Flying" to nodes.

// components/HUD/Omnibox.tsx  
export const Omnibox \= () \=\> (  
  \<div className="absolute top-4 left-1/2 \-translate-x-1/2 w-96 z-50"\>  
    \<div className="relative group"\>  
      \<div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"\>  
        \<SearchIcon className="h-5 w-5 text-slate-400" /\>  
      \</div\>  
      \<input  
        type="text"  
        className="  
          block w-full pl-10 pr-3 py-3  
          bg-white/90 dark:bg-slate-900/90 backdrop-blur-sm  
          border border-slate-200 dark:border-slate-700  
          rounded-full shadow-lg  
          placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500  
          transition-shadow  
        "  
        placeholder="Search papers, authors, or topics... (Cmd+K)"  
      /\>  
      \<div className="absolute inset-y-0 right-0 pr-3 flex items-center"\>  
        \<kbd className="inline-flex items-center border border-slate-200 rounded px-2 text-xs font-sans font-medium text-slate-400"\>  
          ⌘K  
        \</kbd\>  
      \</div\>  
    \</div\>  
  \</div\>  
);

### **Accessibility (A11y) Strategy**

WebGL Canvases are "black boxes" to screen readers. We must provide an alternative view.

1. **Toggle View**: A prominent button to switch between "Graph View" and "List View".  
2. **Semantic Fallback**: When in List View, render the currently visible nodes as a standard HTML \<table\> or \<ul\>.  
3. **Keyboard Navigation**: The Omnibox and Side Panel must be fully navigable via Tab keys.

// components/HUD/ViewToggle.tsx  
export const ViewToggle \= ({ mode, setMode }) \=\> (  
  \<button   
    onClick={() \=\> setMode(mode \=== 'graph' ? 'list' : 'graph')}  
    aria-label={mode \=== 'graph' ? "Switch to List View for screen readers" : "Switch to Graph Visualization"}  
    className="fixed bottom-4 left-4 z-50 p-3 rounded-full bg-blue-600 text-white shadow-lg hover:bg-blue-700"  
  \>  
    {mode \=== 'graph' ? \<ListIcon /\> : \<NetworkIcon /\>}  
  \</button\>  
);

## **8\. Future Roadmap**

* **WebGPU Support**: investigating Cosmograph for 100k+ node support.  
* **Edge Bundling**: To reduce visual clutter on dense graphs.  
* **Time-Travel**: A playback slider to visualize the evolution of citations over time.