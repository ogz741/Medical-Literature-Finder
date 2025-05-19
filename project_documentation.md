# Project Documentation: Medical Literature Discovery Service

## !! LATEST VERSION & ARCHITECTURE (May 2024) !!

**The project has been re-architected to run as a desktop application with a web-based GUI, using `pywebview` and a local Python (FastAPI) backend.**

**All new development for this version is located in the `app/` and `frontend/` directories in the project root.**

This approach aims to:
- Provide an easy-to-use, double-clickable application for non-technical users.
- Avoid platform-specific GUI toolkit issues (like the `_tkinter` problems previously encountered).
- Leverage web technologies (HTML, CSS, JavaScript) for a flexible and modern user interface.

### New Architecture Overview (Project Root):

- **Main Application (`app/main.py`):**
    - Initializes a FastAPI web server (Python).
    - Starts the FastAPI server in a background thread.
    - Creates a `pywebview` window that loads the frontend from the local FastAPI server.
- **Backend (`app/`):
    - **FastAPI (`main.py`, `api_routes.py`):** Serves the frontend and provides API endpoints for all application logic.
    - **Core Logic Modules (`database_manager.py`, `ranking_handler.py`, `pubmed_handler.py`):** Handle data storage, journal ranking scraping/caching, and PubMed interactions. These are largely adapted from previous versions.
- **Frontend (`frontend/`):
    - **HTML (`templates/index.html`):** The main structure of the application interface.
    - **CSS/JavaScript (`static/`):** Styles and client-side interactivity.
- **Dependencies (`requirements.txt` in project root):** Includes `fastapi`, `uvicorn`, `pywebview`, `requests`, `beautifulsoup4`, `biopython`.

**The information below this section pertains to previous architectural explorations, such as the CustomTkinter-based `/MedicalLiteratureApp` attempt or the original standalone FastAPI web service structure. It is kept for historical context, but the primary focus is now on the current `pywebview`-based implementation in the root `app/` and `frontend/` directories.**

## 1. Overview (Original & Standalone GUI Attempts)

This project, originally centered around a Python FastAPI backend, serves as a Medical Literature Discovery Service. Its primary function is to help users find relevant medical research articles from PubMed. The service allows users to:

*   Retrieve rankings of medical journals by specialty (scraped from ooir.org, with fallback sample data).
*   Manage a list of Medical Subject Headings (MeSH terms), pre-populated with terms related to Medical Education.
*   Search PubMed for articles within top-ranked journals, filtered by a specified date range and selected MeSH terms.

The backend is designed with robust fallback mechanisms, providing sample data if external services (like ooir.org or PubMed) are unavailable or return no results, ensuring a consistent user experience, particularly for demonstration purposes.

## 2. Backend (`Medical-Journal-Scraper/backend/server.py`)

### 2.1. Technology Stack (Currently Utilized in `server.py`)

*   **Web Framework:** FastAPI
*   **HTTP Clients:** `requests`, `aiohttp`
*   **HTML Parsing:** `BeautifulSoup4`
*   **PubMed Integration:** `BioPython` (specifically `Bio.Entrez`)
*   **Database:** MongoDB (via `motor` async driver) for MeSH term storage.
*   **Data Validation:** Pydantic
*   **Environment Management:** `python-dotenv`
*   **Concurrency:** `asyncio`

### 2.2. Core Functionalities

*   **Journal Ranking Endpoint (`GET /api/journals/{specialty}`):**
    *   Scrapes journal impact factors and rankings from `https://ooir.org/journals.php`.
    *   Defaults to "Ophthalmology" if no specialty is provided.
    *   Includes hardcoded fallback data for Ophthalmology journals if scraping fails.
*   **MeSH Term Management Endpoints:**
    *   `GET /api/mesh-terms`: Retrieves all MeSH terms from MongoDB.
    *   `POST /api/mesh-terms`: Adds a new MeSH term to MongoDB.
    *   `DELETE /api/mesh-terms/{term_id}`: Deletes a MeSH term from MongoDB.
    *   On startup, the database is initialized with a default list of MeSH terms relevant to "Medical Education" if the collection is empty.
*   **Article Search Endpoint (`POST /api/search`):**
    *   Accepts search parameters: `top_journals` (int), `start_date` (date), `end_date` (date), `mesh_terms` (List[str], optional).
    *   Retrieves journal rankings (using the `/api/journals` logic).
    *   Fetches articles from PubMed using `Bio.Entrez` for the top N journals within the specified date range.
    *   Filters the retrieved articles based on the provided MeSH terms (or all database MeSH terms if none are provided by the user).
    *   If the PubMed search yields no results or fails, it generates and returns a list of sample demo articles (themed around Ophthalmology education) to ensure the API always provides a response.
    *   Returns a `SearchResults` object containing total articles found, MeSH-matched articles, and the list of matched articles.

### 2.3. Data Models (Pydantic)

*   `JournalRanking`: Stores journal name, impact factor, and rank.
*   `MeshTerm`: Stores MeSH term string and its ID.
*   `SearchParameters`: Defines the input for the article search.
*   `Article`: Defines the structure for PubMed article data (PMID, title, journal, publication date, authors, MeSH terms, abstract, URL).
*   `SearchResults`: Defines the output structure for the search endpoint.

### 2.4. Environment Variables (`.env` file in `backend` directory)

*   `MONGO_URL`: Connection string for MongoDB.
*   `DB_NAME`: Name of the MongoDB database.
*   `PUBMED_API_KEY`: API key for PubMed (NCBI Entrez).

## 3. Frontend (Placeholder)

(Details about the frontend architecture, technologies, and interaction with the backend API will be added here once available.)

## 4. Other Components & Dependencies (Potential Future Scope)

The main `requirements.txt` in the `Medical-Journal-Scraper` root directory lists several dependencies not currently utilized by the `backend/server.py`. These include:

*   `supabase`
*   `redis`
*   `boto3` (AWS SDK)
*   `litellm`, `langsmith`