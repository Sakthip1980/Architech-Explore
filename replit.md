# ArchSim - System Architecture Simulator

## Overview

ArchSim is a modular system architecture simulation and exploration tool. It provides a visual drag-and-drop interface for designing computer system architectures (CPUs, memory hierarchies, interconnects, accelerators) and runs Python-based simulations to analyze performance metrics like latency, bandwidth, and power consumption.

The application combines a React-based visual flow editor with a Python simulation backend, allowing users to build hardware system graphs and simulate their behavior under different workloads.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **React + TypeScript** single-page application built with Vite
- **React Flow** library for the node-based visual graph editor where users drag-and-drop hardware components
- **Tailwind CSS v4** with a dark engineering theme and custom CSS variables
- **shadcn/ui** component library (New York style) with Radix UI primitives
- **Wouter** for lightweight client-side routing
- **TanStack React Query** for server state management and API calls
- **React Hook Form** for form handling in the properties panel

### Backend Architecture
- **Express.js** server with TypeScript
- **Python simulator bridge** - Node.js spawns Python processes to run simulations via `simulator_bridge.py`
- The simulator API (`simulator_api.py`) translates graph data from the frontend into Python hardware module instances
- State persistence via JSON file (`.simulator_state.json`) for maintaining system configuration between API calls

### Data Flow
1. User creates/modifies architecture graph in React Flow editor
2. Frontend sends graph data (nodes + edges) to Express API
3. Express spawns Python process with graph data as CLI argument
4. Python builds hardware system from graph, runs simulation cycles
5. Results (latency, bandwidth, power metrics) returned to frontend

### Simulation Engine (Python)
- Located in `/simulator/` directory
- Base `Module` class with abstract `process_request()` method
- Hardware models: DRAM, HBM, SRAM Cache, NVM, Scratchpad (memory); CPU, GPU, NPU, DSP (compute); AXI, PCIe, CXL, NoC (interconnects); DMA, Memory Controller (specialized)
- `System` class orchestrates simulation, generates workloads, collects metrics

### Key Design Patterns
- **Component-based architecture** - Hardware modules are self-contained with their own timing/power models
- **Bridge pattern** - Node.js to Python communication via CLI/JSON for simulation execution
- **In-memory storage** - User data stored in memory (MemStorage class), database schema exists but storage implementation uses Maps

## External Dependencies

### Database
- **PostgreSQL** with Drizzle ORM configured (schema in `shared/schema.ts`)
- Currently uses in-memory storage (`MemStorage`) - database integration ready but not active
- Schema includes basic user table with id, username, password

### Third-Party Services
- No external API integrations
- No authentication services configured (basic user schema exists)

### Key NPM Packages
- `reactflow` - Visual node-based graph editor
- `drizzle-orm` + `drizzle-zod` - Database ORM and schema validation
- `@tanstack/react-query` - Server state management
- `express` - HTTP server
- Full shadcn/ui component set (dialogs, forms, tabs, etc.)

### Python Dependencies
- Standard library only (no requirements.txt visible)
- Simulator is self-contained with no external Python packages