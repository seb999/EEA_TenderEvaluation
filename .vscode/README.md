# VS Code Configuration

This folder contains VS Code configurations for the Tender Evaluation project.

## Debug Configurations

Access these via the Run and Debug panel (Ctrl+Shift+D) or F5:

### 1. Python: FastAPI Service
- Starts the Python FastAPI backend with debugging enabled
- Runs on `http://127.0.0.1:8000`
- Supports breakpoints and step-through debugging
- Auto-reloads on code changes

### 2. React: Vite Dev Server
- Starts the React development server with Vite
- Runs on `http://localhost:5173` (or next available port)
- Automatically opens in browser when ready
- Supports hot module replacement (HMR)

### 3. Full Stack: React + Python API (Compound)
- Starts both the Python service and React dev server simultaneously
- Recommended for full-stack development
- Both services run in separate terminal panels

## Tasks

Access these via Terminal > Run Task or Ctrl+Shift+B:

- **Install Python Dependencies** - Installs packages from `service/requirements.txt`
- **Install Node Dependencies** - Runs `npm install`
- **Start Python Service** - Starts FastAPI backend (non-debug mode)
- **Start React Dev Server** - Starts Vite dev server (non-debug mode)
- **Start Full Stack** - Starts both services (non-debug mode)

## Quick Start

1. **First time setup:**
   - Press `Ctrl+Shift+P` and run "Python: Select Interpreter"
   - Choose the interpreter at `service/venv/Scripts/python.exe`
   - Install recommended extensions when prompted

2. **Start development:**
   - Press `F5` and select "Full Stack: React + Python API"
   - Or click the Run and Debug icon and select the configuration

3. **Debug specific service:**
   - Use "Python: FastAPI Service" to debug only the backend
   - Use "React: Vite Dev Server" to debug only the frontend

## Recommended Extensions

When you open this project, VS Code will recommend installing useful extensions. These include:
- Python support (Python, Pylance, Debugpy)
- JavaScript/TypeScript/React support (ESLint, Prettier)
- Environment file support (.env syntax highlighting)

## Settings

The `settings.json` file includes:
- Python virtual environment configuration
- Format on save for code consistency
- ESLint auto-fix on save
- File exclusions for cleaner workspace
