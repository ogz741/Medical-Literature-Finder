# Medical Journal Scraper (Webview Edition)

This application helps users discover medical literature by searching PubMed and leveraging journal rankings. It runs as a local web application packaged within a desktop webview window, providing a user-friendly GUI.

## Architecture

- **Backend**: Python with FastAPI, serving a local API.
- **Frontend**: HTML, CSS, and JavaScript, rendered in a `pywebview` window.
- **Data Storage**: SQLite database for caching and configuration.

## Core Functionality

- Retrieve journal rankings by specialty (scraped from ooir.org, with caching and fallbacks).
- Manage a list of Medical Subject Headings (MeSH terms).
- Search PubMed for articles based on selected journals, date ranges, and MeSH terms.
- Store user configuration (Entrez email, PubMed API key).

## Setup & Running

1.  **Create a virtual environment** (recommended):
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```
2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the application**:
    ```bash
    python -m app.main
    ```
    This will start the local FastAPI server and open the `pywebview` window.

## Directory Structure

- `app/`: Contains the Python backend code (FastAPI, pywebview integration, logic handlers, database manager).
  - `main.py`: Main entry point, starts FastAPI server and pywebview window.
  - `api_routes.py`: Defines FastAPI API endpoints.
  - `database_manager.py`: SQLite database interactions.
  - `ranking_handler.py`: Logic for fetching and caching journal rankings.
  - `pubmed_handler.py`: Logic for interacting with PubMed API.
- `frontend/`: Contains the HTML, CSS, and JavaScript for the user interface.
  - `templates/index.html`: The main HTML file for the application.
  - `static/`: For CSS, JavaScript, and other static assets.
- `requirements.txt`: Python dependencies.
- `README.md`: This file. 