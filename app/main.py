import webview
import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse # Or FileResponse for serving index.html
from fastapi.templating import Jinja2Templates
import threading
import logging
import os # For path joining
from pathlib import Path
from contextlib import asynccontextmanager
from .api_routes import router as api_router # We'll create this file next

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: No initialization needed
    
    # Yield control back to FastAPI
    yield
    
    # Shutdown: cleanup code would go here
    logger.info("Application shutting down")

# --- FastAPI App Setup ---
app = FastAPI(title="Medical Journal Scraper Backend", lifespan=lifespan)

# Determine base directory for frontend files
# This script is in MedicalJournalScraper/app/main.py
# Frontend is in MedicalJournalScraper/frontend/
BASE_DIR = Path(__file__).resolve().parent.parent # This should be MedicalJournalScraper directory
STATIC_FILES_DIR = BASE_DIR / "frontend" / "static"
TEMPLATES_DIR = BASE_DIR / "frontend" / "templates"

# Mount static files (CSS, JS)
if STATIC_FILES_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_FILES_DIR), name="static")
    logger.info(f"Mounted static files from {STATIC_FILES_DIR}")
else:
    logger.warning(f"Static files directory not found: {STATIC_FILES_DIR}")

# Setup for Jinja2 templates (for serving index.html primarily)
if TEMPLATES_DIR.exists():
    templates = Jinja2Templates(directory=TEMPLATES_DIR)
    logger.info(f"Templates directory configured: {TEMPLATES_DIR}")
else:
    logger.warning(f"Templates directory not found: {TEMPLATES_DIR}")

# Placeholder for API router - to be created in api_routes.py
app.include_router(api_router, prefix="/api")

# Root endpoint to serve the main HTML page
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    return HTMLResponse("<html><body><h1>Error: Templates not found.</h1><p>Frontend templates directory is missing.</body></html>")

# --- Pywebview Setup ---
# Global variable to hold the Uvicorn server thread
server_thread = None

# Port for the FastAPI server
SERVER_PORT = 8088 # Using a less common port to avoid conflicts
SERVER_URL = f"http://localhost:{SERVER_PORT}"

def run_server():
    """Runs the Uvicorn server."""
    logger.info(f"Starting Uvicorn server on {SERVER_URL}")
    uvicorn.run(app, host="localhost", port=SERVER_PORT, log_level="info")

if __name__ == "__main__":
    logger.info("Application starting...")

    # Start Uvicorn server in a separate thread
    # Daemonizing the thread means it will exit when the main program exits
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    logger.info("FastAPI server thread started.")

    # Create and start the pywebview window
    # This will block until the window is closed
    webview.create_window(
        "Medical Literature Finder",
        SERVER_URL,
        width=1000, # Adjusted width
        height=750, # Adjusted height
        resizable=True,
        # frameless=False, # Optional: for a frameless window
        # easy_drag=True, # Optional: if frameless
        confirm_close=True # Ask user for confirmation before closing
    )
    logger.info("Pywebview window created. Starting GUI...")
    webview.start(debug=True) # debug=True can be helpful for development

    logger.info("Application_finished.") 