import webview
import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import threading
import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager
from .api_routes import router as api_router
import time
import socket

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: No initialization needed
    logger.info("Application starting up...")
    
    # Yield control back to FastAPI
    yield
    
    # Shutdown: cleanup code would go here
    logger.info("Application shutting down")

# --- FastAPI App Setup ---
app = FastAPI(title="Medical Journal Scraper Backend", lifespan=lifespan)

# Determine base directory for frontend files
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_FILES_DIR = BASE_DIR / "frontend" / "static"
TEMPLATES_DIR = BASE_DIR / "frontend" / "templates"

# Mount static files (CSS, JS)
if STATIC_FILES_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_FILES_DIR), name="static")
    logger.info(f"Mounted static files from {STATIC_FILES_DIR}")
else:
    logger.warning(f"Static files directory not found: {STATIC_FILES_DIR}")

# Setup for Jinja2 templates
if TEMPLATES_DIR.exists():
    templates = Jinja2Templates(directory=TEMPLATES_DIR)
    logger.info(f"Templates directory configured: {TEMPLATES_DIR}")
else:
    logger.warning(f"Templates directory not found: {TEMPLATES_DIR}")

# Include API router
app.include_router(api_router, prefix="/api")

# Root endpoint to serve the main HTML page
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    return HTMLResponse("<html><body><h1>Error: Templates not found.</h1></body></html>")

# --- Server Configuration ---
SERVER_PORT = 8088
SERVER_URL = f"http://localhost:{SERVER_PORT}"

def run_server():
    """Runs the Uvicorn server."""
    logger.info(f"Starting Uvicorn server on {SERVER_URL}")
    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT, log_level="info")

def wait_for_server():
    """Wait for the server to start up."""
    max_attempts = 10
    delay = 1  # seconds between attempts
    
    for attempt in range(max_attempts):
        try:
            with socket.create_connection(("localhost", SERVER_PORT), timeout=1):
                logger.info("Server is ready!")
                return True
        except (ConnectionRefusedError, socket.timeout):
            if attempt < max_attempts - 1:  # Don't log on last attempt
                logger.info(f"Waiting for server (attempt {attempt + 1}/{max_attempts})...")
            time.sleep(delay)
    
    logger.error(f"Server failed to start after {max_attempts} attempts")
    return False

if __name__ == "__main__":
    logger.info("Application starting...")

    # Start Uvicorn server in a separate thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    logger.info("FastAPI server thread started.")

    # Wait for the server to be ready
    if not wait_for_server():
        logger.error("Server failed to start within timeout period")
        exit(1)

    # Create and start the pywebview window
    webview.create_window(
        "Medical Literature Finder",
        SERVER_URL,
        width=1000,
        height=750,
        resizable=True,
        confirm_close=True
    )
    logger.info("Pywebview window created. Starting GUI...")
    webview.start(debug=True)

    logger.info("Application finished.")