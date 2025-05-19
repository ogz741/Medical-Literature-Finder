import React, { useState } from 'react';
import { Plus, Minus } from 'lucide-react';
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, Body
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import date, datetime
import logging
from pathlib import Path
import os
import json
from .database_manager import DatabaseManager
from .ranking_handler import RankingHandler
from .pubmed_handler import search_pubmed, search_pubmed_for_download, ArticleDict, fetch_article_details_by_pmid
from fastapi.responses import StreamingResponse
import io
import csv
import openpyxl
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import jwt
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi.security import OAuth2PasswordBearer

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# --- Dependency Functions ---
def get_db_manager() -> DatabaseManager:
    # This will create a new instance for each request that depends on it.
    # For SQLite, this is generally fine as connections are lightweight.
    # If DatabaseManager managed more complex state or heavier connections,
    # you might consider a singleton pattern or FastAPI's app.state.
    return DatabaseManager()

# --- Models ---
class ConfigUpdateRequest(BaseModel):
    entrez_email: Optional[str] = None
    pubmed_api_key: Optional[str] = None

class ConfigResponse(BaseModel):
    entrez_email: Optional[str] = Field(default="") # Provide default for response model
    pubmed_api_key: Optional[str] = Field(default="") # Provide default

class MeSHTermRequest(BaseModel): # For creating MeSH terms
    term: str

class MeSHTermResponse(BaseModel):
    id: str
    term: str

class ArticleSearchRequest(BaseModel):
    journal_specialty: str = Field(default="Ophthalmology", description="Medical specialty for journal ranking if specific journals aren't selected.")
    selected_journals: Optional[List[str]] = Field(default=None, description="Specific list of journal names to search.")
    start_date: date
    end_date: date
    mesh_terms: Optional[List[str]] = Field(default=None, description="List of MeSH terms to filter results by.")
    use_demo_data: bool = Field(default=False, description="Use generated demo data instead of live PubMed search.")
    max_journals_to_search: int = Field(default=5, ge=1, le=20, description="Max number of top-ranked journals to search if not specified by selected_journals.")
    max_articles_per_journal: int = Field(default=10, ge=1, le=50, description="Max articles to fetch from PubMed per journal.")

class DownloadRequest(BaseModel):
    query: Optional[str] = None
    journals: Optional[List[str]] = Field(default_factory=list)
    mesh_terms: Optional[List[str]] = Field(default_factory=list) # Frontend can send, or backend can re-fetch user's MeSH
    filter_date_start: Optional[str] = None
    filter_date_end: Optional[str] = None
    format: str = Field(description="File format: csv, xlsx, json, bibtex")
    max_results: Optional[int] = Field(default=500, ge=1, le=5000, description="Max results for download")

# --- API Endpoints ---

@router.get("/health", summary="Health check endpoint")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# --- Config Endpoints ---
@router.post("/config", response_model=ConfigResponse, summary="Update application configuration")
async def update_app_config(config_data: ConfigUpdateRequest, db_manager: DatabaseManager = Depends(get_db_manager)):
    logger.info(f"Updating config: {config_data.model_dump(exclude_none=True)}")
    updated_email = db_manager.get_config("entrez_email")
    updated_api_key = db_manager.get_config("pubmed_api_key")

    if config_data.entrez_email is not None:
        db_manager.save_config("entrez_email", config_data.entrez_email)
        updated_email = config_data.entrez_email
    if config_data.pubmed_api_key is not None:
        key_to_save = config_data.pubmed_api_key
        if key_to_save.strip().lower() == "your_pubmed_api_key_here":
            key_to_save = ""
        db_manager.save_config("pubmed_api_key", key_to_save)
        updated_api_key = key_to_save
    
    return ConfigResponse(entrez_email=updated_email, pubmed_api_key=updated_api_key)

@router.get("/config", response_model=ConfigResponse, summary="Get current application configuration")
async def get_app_config(db_manager: DatabaseManager = Depends(get_db_manager)):
    logger.info("Fetching current config")
    email = db_manager.get_config("entrez_email", default="")
    api_key = db_manager.get_config("pubmed_api_key", default="")
    return ConfigResponse(entrez_email=email, pubmed_api_key=api_key)

# --- MeSH Term Endpoints ---
@router.get("/mesh-terms", response_model=List[MeSHTermResponse], summary="Get all MeSH terms")
async def get_mesh_terms(db_manager: DatabaseManager = Depends(get_db_manager)):
    try:
        terms_list = db_manager.get_all_mesh_terms()
        # Convert the mesh_id to string id for compatibility with the response model
        return [MeSHTermResponse(id=str(t.get('id', '')), term=t.get('term', '')) for t in terms_list]
    except Exception as e:
        logger.error(f"Error getting MeSH terms: {e}", exc_info=True)
        # Return empty list instead of raising an exception
        return []

@router.post("/mesh-terms", response_model=MeSHTermResponse, status_code=201, summary="Add a new MeSH term")
async def add_new_mesh_term(mesh_term_request: MeSHTermRequest, db_manager: DatabaseManager = Depends(get_db_manager)):
    term_id = db_manager.add_mesh_term(mesh_term_request.term)
    if term_id is None: # Should ideally differentiate between already exists and error
        # Assuming add_mesh_term returns ID of existing if duplicate, or new ID
        # If it truly failed (not duplicate), raise 500. If duplicate, perhaps 409.
        # For now, let's assume if add_mesh_term returns None, it's an issue beyond "already exists".
        # The current db_manager.add_mesh_term returns ID of existing or new. So this path may not be hit if it works.
        existing_term = db_manager.get_mesh_term_by_name(mesh_term_request.term) # Helper needed in DB manager
        if existing_term:
             raise HTTPException(status_code=409, detail=f"MeSH term '{mesh_term_request.term}' already exists with ID {existing_term['id']}.")
        raise HTTPException(status_code=500, detail="Failed to add MeSH term due to an unexpected error.")
    
    return MeSHTermResponse(id=term_id, term=mesh_term_request.term)

@router.delete("/mesh-terms/{term_id}", status_code=204, summary="Delete a MeSH term")
async def delete_mesh_term_by_id(term_id: str, db_manager: DatabaseManager = Depends(get_db_manager)):
    success = db_manager.delete_mesh_term(term_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"MeSH term with ID {term_id} not found.")
    return None # No content

# --- Journal Rankings Endpoints ---
@router.get("/journal-rankings/{specialty}")
async def get_journal_rankings_live(specialty: str, db_manager: DatabaseManager = Depends(get_db_manager)):
    """Get journal rankings for a given specialty - LIVE from ooir.org"""
    try:
        # Instantiate RankingHandler
        entrez_email = db_manager.get_config("entrez_email") 
        handler = RankingHandler(db_manager=db_manager, entrez_email=entrez_email)
        
        # Always fetch live data from OOIR.org
        rankings = handler.fetch_live_journal_rankings(specialty_query=specialty)
            
        if not rankings:
            logger.info(f"No rankings found for specialty: {specialty}")
            return {"status": "success", "data": [], "message": f"No rankings found for {specialty}."}
            
        return {"status": "success", "data": rankings}
    except Exception as e:
        logger.error(f"Error retrieving journal rankings for {specialty}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving journal rankings: {str(e)}")

@router.get("/rankings/{specialty}", response_model=List[Dict[str, Any]], summary="Get journal rankings for a specialty - LIVE from ooir.org")
async def get_rankings_for_specialty_live(specialty: str, db_manager: DatabaseManager = Depends(get_db_manager)):
    logger.info(f"Request for rankings for {specialty}")
    try:
        entrez_email = db_manager.get_config("entrez_email")
        handler = RankingHandler(db_manager=db_manager, entrez_email=entrez_email)
        rankings = handler.fetch_live_journal_rankings(specialty_query=specialty)
        
        if not rankings:
            logger.info(f"No rankings found for specialty: {specialty}")
            return [] 
        return rankings
    except Exception as e:
        logger.error(f"Error fetching rankings for {specialty}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching rankings: {str(e)}")

@router.post("/rankings/{specialty}/refresh", response_model=List[Dict[str, Any]], summary="Force refresh journal rankings for a specialty")
async def refresh_rankings_for_specialty_live(specialty: str, db_manager: DatabaseManager = Depends(get_db_manager)):
    logger.info(f"Request to refresh rankings for {specialty}")
    try:
        entrez_email = db_manager.get_config("entrez_email")
        handler = RankingHandler(db_manager=db_manager, entrez_email=entrez_email)
        rankings = handler.fetch_live_journal_rankings(specialty_query=specialty)

        if not rankings:
             return []
        return rankings
    except Exception as e:
        logger.error(f"Error refreshing rankings for {specialty}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error refreshing rankings: {str(e)}")

# --- Article Search Endpoints ---
@router.post("/search-articles", response_model=List[Dict[str, Any]], summary="Search PubMed articles")
async def search_articles(search_params: ArticleSearchRequest, db_manager: DatabaseManager = Depends(get_db_manager)):
    try:
        from .pubmed_handler import search_pubmed_articles
        
        # Get MeSH terms if needed and not provided
        if not search_params.mesh_terms:
            # Get MeSH terms from database (user's saved terms)
            terms = db_manager.get_all_mesh_terms()
            mesh_terms = [term["term"] for term in terms]
            search_params.mesh_terms = mesh_terms
        
        # Get configuration for PubMed API
        email = db_manager.get_config("entrez_email", default="")
        api_key = db_manager.get_config("pubmed_api_key", default="")
        
        # Search articles
        results = await search_pubmed_articles(
            search_params, 
            email=email, 
            api_key=api_key,
            db_manager=db_manager  # Pass the database manager
        )
        return results
    except Exception as e:
        logger.error(f"Error searching articles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error searching articles: {str(e)}")

@router.get("/search-mesh")
async def search_mesh_terms(term: str, max_results: int = 10):
    """Search MeSH terms by keyword"""
    try:
        results = get_mesh_terms(term, max_results)
        return {"status": "success", "results": results}
    except Exception as e:
        logger.error(f"Error in MeSH search: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search-pubmed")
async def search_pubmed_api(
    query: Optional[str] = None,
    page: int = 1, 
    per_page: int = 10, 
    sort: Optional[str] = None,
    filter_date_start: Optional[str] = None,
    filter_date_end: Optional[str] = None,
    journals: Optional[str] = None,  # Comma-separated list of journal names
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """Search PubMed articles with the given query"""
    try:
        journal_list = []
        if journals:
            journal_list = [j.strip() for j in journals.split(',') if j.strip()]
        
        # Get email and API key from database
        email = db_manager.get_config("entrez_email", default="")
        api_key = db_manager.get_config("pubmed_api_key", default="")

        # Get user's selected MeSH terms from database
        user_mesh_terms_records = db_manager.get_all_mesh_terms()
        user_mesh_terms_list = [term_record.get("term") for term_record in user_mesh_terms_records if term_record.get("term")]
        
        actual_query = query if query is not None else "" # Use an empty string if query is None

        # Frontend already ensures that either actual_query or user_mesh_terms_list (or both) will have content.
        # If actual_query is empty, the search will rely on user_mesh_terms_list.
        # If both were empty, the frontend would not have initiated this API call.

        results = await search_pubmed(
            query=actual_query, 
            page=page, 
            per_page=per_page, 
            sort=sort,
            filter_date_start=filter_date_start,
            filter_date_end=filter_date_end,
            journal_filter=journal_list,
            mesh_terms_filter=user_mesh_terms_list, # Pass fetched MeSH terms
            entrez_email=email,
            api_key=api_key
        )
        
        # Add to search history only if there was an actual query or MeSH terms were used for the search
        # The original query (potentially None) is what the user intended.
        # For history, maybe log the effective search (e.g. "MeSH search: [terms]" if query was empty)
        # For now, let's stick to logging the original query if present, or a generic MeSH search.
        
        log_query_for_history = query # The original input from user
        if not log_query_for_history and user_mesh_terms_list:
            log_query_for_history = f"(MeSH terms: {', '.join(user_mesh_terms_list[:3])}{'...' if len(user_mesh_terms_list) > 3 else ''})"
        
        if log_query_for_history: # Only log if there was some criteria
            db_manager.add_to_search_history(log_query_for_history, results.get("total", 0))
        
        return {"status": "success", "results": results}
    except Exception as e:
        logger.error(f"Error in PubMed search: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/available-dates")
async def get_available_dates(db_manager: DatabaseManager = Depends(get_db_manager)):
    """Get available dates for journal rankings"""
    try:
        # Since we now always fetch live data, just return "latest"
        dates = ["latest"]
        return {"status": "success", "dates": dates}
    except Exception as e:
        logger.error(f"Error retrieving available dates: {e}")
        return {"status": "error", "message": f"Error retrieving dates: {str(e)}"}

@router.get("/available-specialties")
async def get_available_specialties(db_manager: DatabaseManager = Depends(get_db_manager)):
    """Get list of available medical specialties"""
    try:
        # Get from database first
        db_specialties = db_manager.get_available_specialties()
        
        # Combine with hardcoded specialties
        hardcoded_specialties = [
            "Allergy", "Andrology", "Anesthesiology", "Cardiology", "Dermatology",
            "Emergency Medicine", "Endocrinology", "Gastroenterology", "Geriatrics",
            "Gynecology", "Hematology", "Immunology", "Infectious Diseases",
            "Internal Medicine", "Nephrology", "Neurology", "Neurosurgery",
            "Obstetrics", "Oncology", "Ophthalmology", "Orthopedics",
            "Otolaryngology", "Pathology", "Pediatrics", "Physical Medicine",
            "Plastic Surgery", "Psychiatry", "Pulmonology", "Radiology",
            "Rheumatology", "Sports Medicine", "Surgery", "Toxicology",
            "Transplantation", "Urology", "Vascular Medicine"
        ]
        
        # Combine and deduplicate
        all_specialties = list(set(db_specialties + hardcoded_specialties))
        all_specialties.sort()
        
        return {"status": "success", "specialties": all_specialties}
    except Exception as e:
        logger.error(f"Error retrieving specialties: {e}", exc_info=True)
        return {"status": "error", "message": f"Error retrieving specialties: {str(e)}"}

@router.post("/clear-cache")
async def clear_cache(cache_type: str = "all", db_manager: DatabaseManager = Depends(get_db_manager)):
    """Clear the application cache"""
    try:
        result = db_manager.clear_cache(cache_type)
        
        # Remove file cache if it exists (though our new implementation doesn't use it)
        if cache_type in ("rankings", "all"):
            rankings_cache_dir = Path(__file__).parent / "rankings_cache"
            if rankings_cache_dir.exists():
                for file in rankings_cache_dir.glob("*.json"):
                    try:
                        os.remove(file)
                        logger.info(f"Removed cache file: {file.name}")
                    except Exception as e:
                        logger.error(f"Error removing cache file {file.name}: {e}")
        
        return {"status": "success", "message": f"Cache cleared: {cache_type}"}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get-preferences")
async def get_user_preferences(db_manager: DatabaseManager = Depends(get_db_manager)):
    """Get user preferences"""
    try:
        preferences = {}
        keys = ["default_specialty", "default_sort", "theme", "results_per_page"]
        
        for key in keys:
            preferences[key] = db_manager.get_preference(key)
            
        return {"status": "success", "preferences": preferences}
    except Exception as e:
        logger.error(f"Error getting preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save-preferences")
async def save_user_preferences(preferences: Dict[str, Any] = Body(...), db_manager: DatabaseManager = Depends(get_db_manager)):
    """Save user preferences"""
    try:
        for key, value in preferences.items():
            db_manager.save_preference(key, value)
            
        return {"status": "success", "message": "Preferences saved"}
    except Exception as e:
        logger.error(f"Error saving preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search-history")
async def get_search_history(limit: int = 10, db_manager: DatabaseManager = Depends(get_db_manager)):
    """Get recent search history"""
    try:
        history = db_manager.get_search_history(limit)
        return {"status": "success", "history": history}
    except Exception as e:
        logger.error(f"Error retrieving search history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bookmarked-articles")
async def get_bookmarked_articles(db_manager: DatabaseManager = Depends(get_db_manager)):
    """Get all bookmarked articles"""
    try:
        bookmarks = db_manager.get_bookmarked_articles()
        return {"status": "success", "bookmarks": bookmarks}
    except Exception as e:
        logger.error(f"Error retrieving bookmarked articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bookmark-article")
async def bookmark_article(article: Dict[str, Any] = Body(...), db_manager: DatabaseManager = Depends(get_db_manager)):
    """Bookmark an article"""
    try:
        result = db_manager.bookmark_article(
            pmid=article.get("pmid", ""),
            title=article.get("title", ""),
            authors=article.get("authors", ""),
            journal=article.get("journal", ""),
            pub_date=article.get("pub_date", ""),
            abstract=article.get("abstract", "")
        )
        
        if result:
            return {"status": "success", "message": "Article bookmarked"}
        else:
            return {"status": "error", "message": "Failed to bookmark article"}
    except Exception as e:
        logger.error(f"Error bookmarking article: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/bookmark-article/{pmid}")
async def remove_bookmark(pmid: str, db_manager: DatabaseManager = Depends(get_db_manager)):
    """Remove an article bookmark"""
    try:
        result = db_manager.remove_article_bookmark(pmid)
        
        if result:
            return {"status": "success", "message": "Bookmark removed"}
        else:
            return {"status": "error", "message": "Bookmark not found"}
    except Exception as e:
        logger.error(f"Error removing bookmark: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get-dates-for-specialty/{specialty}")
async def get_dates_for_specialty(specialty: str, db_manager: DatabaseManager = Depends(get_db_manager)):
    """Get available dates for a specific specialty"""
    try:
        # Since we now always fetch live data, just return "latest"
        dates = ["latest"] 
        return {"status": "success", "dates": dates}
    except Exception as e:
        logger.error(f"Error retrieving dates for specialty: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Helper functions for file generation ---

def generate_csv_content(articles: List[ArticleDict]) -> str:
    output = io.StringIO()
    if not articles:
        return ""
    
    # Define headers based on ArticleDict structure - ensure all relevant fields are included
    # Taking common fields, adjust as necessary from ArticleDict keys
    headers = list(articles[0].keys()) if articles else [
        "pubmed_id", "title", "journal", "publication_date", 
        "authors", "mesh_terms", "abstract", "url", "impact_factor"
    ]
    
    writer = csv.DictWriter(output, fieldnames=headers, extrasaction='ignore')
    writer.writeheader()
    for article in articles:
        # Ensure authors and mesh_terms are comma-separated strings for CSV
        row_data = article.copy()
        if isinstance(row_data.get("authors"), list):
            row_data["authors"] = ", ".join(row_data["authors"])
        if isinstance(row_data.get("mesh_terms"), list):
            row_data["mesh_terms"] = ", ".join(row_data["mesh_terms"])
        writer.writerow(row_data)
    return output.getvalue()

def generate_xlsx_content(articles: List[ArticleDict]) -> bytes:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    if not articles:
        output = io.BytesIO()
        workbook.save(output)
        return output.getvalue()

    headers = list(articles[0].keys()) if articles else [
        "pubmed_id", "title", "journal", "publication_date", 
        "authors", "mesh_terms", "abstract", "url", "impact_factor"
    ]
    sheet.append(headers)

    for article in articles:
        row_data = []
        for header in headers:
            value = article.get(header)
            if isinstance(value, list):
                value = ", ".join(value) # Convert lists to string for Excel
            elif isinstance(value, (dict, set)): # Should not happen if ArticleDict is flat
                 value = str(value)
            row_data.append(value)
        sheet.append(row_data)
    
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()

def generate_json_content(articles: List[ArticleDict]) -> str:
    return json.dumps(articles, indent=2)

def format_authors_for_bibtex(authors_list: List[str]) -> str:
    if not authors_list:
        return ""
    # BibTeX expects authors separated by "and"
    # Assuming authors are in "FirstName LastName" or "LastName, FirstName" format.
    # A simple join, more sophisticated parsing might be needed for complex names.
    return " and ".join(authors_list)

def generate_bibtex_content(articles: List[ArticleDict]) -> str:
    bibtex_entries = []
    for article in articles:
        pmid_raw = article.get("pubmed_id", "")
        # Ensure BibTeX key is valid: replace dots, no spaces, basic sanitization
        pmid_key_part = pmid_raw.replace(".", "_").replace(" ", "")
        
        title_first_word = article.get('title', 'untitled').split(' ')[0].lower()
        # Sanitize title_first_word for key (remove non-alphanumeric)
        title_key_part = ''.join(filter(str.isalnum, title_first_word))

        # Add a small random part to ensure uniqueness if other parts are identical
        random_suffix = datetime.now().strftime('%f')[:3] # Microseconds first 3 digits
        entry_key = f"pubmed_{pmid_key_part if pmid_key_part else title_key_part}_{random_suffix}"

        entry_parts = [f"@article{{{entry_key},", ]

        title = article.get("title")
        if title:
            # Escape existing braces in title, then wrap with one set
            safe_title = title.replace("{", "\\{").replace("}", "\\}")
            entry_parts.append(f"  title = {{{safe_title}}},",)

        authors = article.get("authors", [])
        if authors:
            # Authors should be 'Last, First and Last, First'
            # Simple join for now, assuming names are somewhat clean
            authors_str = " and ".join(authors)
            safe_authors = authors_str.replace("{", "\\{").replace("}", "\\}")
            entry_parts.append(f"  author = {{{safe_authors}}},",)

        journal = article.get("journal")
        if journal:
            safe_journal = journal.replace("{", "\\{").replace("}", "\\}")
            entry_parts.append(f"  journal = {{{safe_journal}}},",)
        
        publication_date = article.get("publication_date", "")
        year = ""
        month = ""
        if publication_date:
            try:
                dt_obj = datetime.strptime(publication_date, "%Y-%m-%d")
                year = str(dt_obj.year)
                month = dt_obj.strftime("%b") # Jan, Feb, etc.
            except ValueError:
                if "-" in publication_date:
                    year = publication_date.split("-")[0]
                else: # Handle cases like only year e.g. "2023"
                    year = publication_date 

        if year:
            entry_parts.append(f"  year = {{{year}}},",)
        if month: # BibTeX often uses month abbreviations
            entry_parts.append(f"  month = {{{month}}},",)

        pmid = article.get("pubmed_id")
        if pmid: # Using 'note' or 'annote' is common for PMID
             entry_parts.append(f"  note = {{PMID: {pmid}}},",)
        
        url = article.get("url")
        if url:
            entry_parts.append(f"  url = {{{url}}},",)
        
        abstract = article.get("abstract")
        if abstract and abstract != "No abstract available.": # Some BibTeX styles/tools use the abstract field
            safe_abstract = abstract.replace("{", "\\{").replace("}", "\\}")
            entry_parts.append(f"  abstract = {{{safe_abstract}}},",)

        # Remove trailing comma from the last actual field
        if entry_parts[-1].endswith(","):
            entry_parts[-1] = entry_parts[-1][:-1]
        
        entry_parts.append("}")
        bibtex_entries.append("\n".join(entry_parts))
        
    return "\n\n".join(bibtex_entries)

def generate_single_bibtex_entry(article: ArticleDict) -> str:
    """Generates a single BibTeX entry for an article."""
    if not article:
        return ""

    pmid_raw = article.get("pubmed_id", "")
    pmid_key_part = pmid_raw.replace(".", "_").replace(" ", "")
    title_first_word = article.get('title', 'untitled').split(' ')[0].lower()
    title_key_part = ''.join(filter(str.isalnum, title_first_word))
    # Use a more consistent key if pmid is available, otherwise fallback to title + timestamp
    entry_key = f"pubmed_{pmid_key_part}" if pmid_key_part else f"article_{title_key_part}_{datetime.now().strftime('%f')[:3]}"

    entry_parts = [f"@article{{{entry_key},"] # BibTeX entry type

    title = article.get("title")
    if title:
        safe_title = title.replace("{", "\\{").replace("}", "\\}")
        entry_parts.append(f"  title = {{{safe_title}}},",)

    authors = article.get("authors", []) # Expecting a list of strings
    if authors:
        # Authors should be 'Last, First and Last, First' or simply joined by 'and'
        authors_str = " and ".join(authors) if isinstance(authors, list) else str(authors)
        safe_authors = authors_str.replace("{", "\\{").replace("}", "\\}")
        entry_parts.append(f"  author = {{{safe_authors}}},",)

    journal = article.get("journal")
    if journal:
        safe_journal = journal.replace("{", "\\{").replace("}", "\\}")
        entry_parts.append(f"  journal = {{{safe_journal}}},",)
    
    publication_date = article.get("publication_date", "")
    year = ""
    month_str = ""
    if publication_date: # Assuming YYYY-MM-DD or YYYY-MM or YYYY format
        parts = publication_date.split('-')
        if len(parts) >= 1 and parts[0].isdigit():
            year = parts[0]
        if len(parts) >= 2:
            try:
                month_num = int(parts[1])
                month_str = datetime(int(year), month_num, 1).strftime("%b") # Jan, Feb
            except ValueError:
                pass # Keep month_str empty if month is not valid
    
    if year:
        entry_parts.append(f"  year = {{{year}}},",)
    if month_str: 
        entry_parts.append(f"  month = {{{month_str}}},",)

    # Volume, Issue, Pages - these are often not in basic PubMed efetch, might need detailed parsing or be omitted
    # volume = article.get("volume")
    # if volume: entry_parts.append(f"  volume = {{{volume}}},",)
    # number = article.get("issue") # or number
    # if number: entry_parts.append(f"  number = {{{number}}},",)
    # pages = article.get("pages")
    # if pages: entry_parts.append(f"  pages = {{{pages}}},",)

    pmid = article.get("pubmed_id")
    if pmid: 
         entry_parts.append(f"  pmid = {{{pmid}}},",)
    
    url = article.get("url")
    if url:
        entry_parts.append(f"  url = {{{url}}},",)
    
    abstract = article.get("abstract")
    if abstract and abstract.lower() != "no abstract available.":
        safe_abstract = abstract.replace("{", "\\{").replace("}", "\\}")
        entry_parts.append(f"  abstract = {{{safe_abstract}}},",)

    if entry_parts[-1].endswith(","):
        entry_parts[-1] = entry_parts[-1][:-1]
    
    entry_parts.append("}")
    return "\n".join(entry_parts)

@router.post("/download-search-results", summary="Download search results in specified format")
async def download_search_results(params: DownloadRequest, db_manager: DatabaseManager = Depends(get_db_manager)):
    logger.info(f"Download request received: Format={params.format}, Query='{params.query}', MaxResults={params.max_results}")

    email = db_manager.get_config("entrez_email", default="")
    api_key = db_manager.get_config("pubmed_api_key", default="")

    if not email:
        raise HTTPException(status_code=400, detail="Entrez email is not configured. Please set it in Settings.")

    # If MeSH terms are not provided in request, fetch user's selected MeSH terms
    mesh_terms_to_use = params.mesh_terms
    if not mesh_terms_to_use: # If list is empty or None
        user_mesh_records = db_manager.get_all_mesh_terms()
        mesh_terms_to_use = [record.get("term") for record in user_mesh_records if record.get("term")]
        logger.info(f"No MeSH terms in download request, using user's saved MeSH: {mesh_terms_to_use}")
    
    articles = await search_pubmed_for_download(
        query=params.query if params.query else "", # Ensure query is not None
        journal_filter=params.journals,
        mesh_terms_filter=mesh_terms_to_use,
        filter_date_start=params.filter_date_start,
        filter_date_end=params.filter_date_end,
        entrez_email=email,
        api_key=api_key,
        max_results=params.max_results
    )

    if not articles:
        logger.info("No articles found for download based on criteria.")
        # Return empty content for the chosen format or an error?
        # For now, let's return empty content for the chosen format.
        # Alternatively, raise HTTPException(status_code=404, detail="No articles found matching criteria")

    content = b""
    media_type = "application/octet-stream"
    filename = f"pubmed_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    if params.format == "csv":
        csv_data = generate_csv_content(articles)
        content = csv_data.encode("utf-8")
        media_type = "text/csv"
        filename += ".csv"
    elif params.format == "xlsx":
        content = generate_xlsx_content(articles)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename += ".xlsx"
    elif params.format == "json":
        json_data = generate_json_content(articles)
        content = json_data.encode("utf-8")
        media_type = "application/json"
        filename += ".json"
    elif params.format == "bibtex":
        bibtex_data = generate_bibtex_content(articles)
        content = bibtex_data.encode("utf-8")
        media_type = "application/x-bibtex" # Common BibTeX MIME type
        filename += ".bib"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file format: {params.format}")

    if not content and articles: # Content generation failed but articles were present
        logger.error(f"Content generation failed for format {params.format} despite having articles.")
        raise HTTPException(status_code=500, detail="Failed to generate file content.")
    
    if not content and not articles: # No articles and no content (e.g. empty CSV header)
        # Return a response indicating no data, or a 204 No Content if appropriate
        # For now, returning an empty file might be acceptable for some formats.
        # Let's return an empty response with appropriate headers, or a 204.
        # FastAPI's StreamingResponse requires content, so we send minimal valid content.
        if params.format == "csv": content = "\n".encode("utf-8") # Empty CSV
        elif params.format == "xlsx": # Empty XLSX
            workbook = openpyxl.Workbook()
            output = io.BytesIO()
            workbook.save(output)
            content = output.getvalue()
        elif params.format == "json": content = "[]".encode("utf-8") # Empty JSON array
        elif params.format == "bibtex": content = "".encode("utf-8") # Empty BibTeX
        
        # If still no content after trying to make minimal valid empty file:
        if not content: 
             return Response(status_code=204) # No content to send back


    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    ) 

@router.get("/cite-article/{pmid}", summary="Get .nbib citation for a single article")
async def cite_article(pmid: str, db_manager: DatabaseManager = Depends(get_db_manager)):
    logger.info(f"Citation request received for PMID: {pmid}")

    email = db_manager.get_config("entrez_email", default="")
    api_key = db_manager.get_config("pubmed_api_key", default="")

    if not email:
        raise HTTPException(status_code=400, detail="Entrez email is not configured. Please set it in Settings.")

    article_details = await fetch_article_details_by_pmid(pmid, entrez_email=email, api_key=api_key)

    if not article_details:
        logger.error(f"Could not fetch details for PMID {pmid} for citation.")
        raise HTTPException(status_code=404, detail=f"Article with PMID {pmid} not found or details could not be fetched.")

    bibtex_content = generate_single_bibtex_entry(article_details)
    
    if not bibtex_content:
        logger.error(f"Failed to generate BibTeX content for PMID {pmid}.")
        raise HTTPException(status_code=500, detail="Failed to generate citation content.")

    # Sanitize title for filename more carefully
    safe_title_part = "article"
    if article_details.get("title"):
        safe_title_part = ''.join(c if c.isalnum() or c in (' ', '-') else '' for c in article_details.get("title"))[:30].strip().replace(' ', '_')
    
    filename = f"cite_{pmid}_{safe_title_part}.nbib"
    
    return StreamingResponse(
        io.BytesIO(bibtex_content.encode("utf-8")),
        media_type="application/x-bibtex", # Standard BibTeX MIME type
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    ) 

# Add new PDF generation endpoint
@router.post("/download-pdf")
async def download_pdf(articles: List[Dict[str, Any]]):
    """Generate PDF from article list"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Create custom style for article titles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        spaceAfter=20
    )
    
    # Build PDF content
    elements = []
    
    # Add header
    elements.append(Paragraph("Medical Literature Search Results", styles['Title']))
    elements.append(Spacer(1, 20))
    
    # Add articles
    for article in articles:
        # Article title
        elements.append(Paragraph(article['title'], title_style))
        
        # Authors and journal
        if article.get('authors'):
            authors = ', '.join(article['authors'])
            elements.append(Paragraph(f"Authors: {authors}", styles['Normal']))
        elements.append(Paragraph(f"Journal: {article['journal']}", styles['Normal']))
        
        # Publication date and PMID
        elements.append(Paragraph(
            f"Published: {article['publication_date']} | PMID: {article['pubmed_id']}", 
            styles['Normal']
        ))
        
        # Abstract
        if article.get('abstract'):
            elements.append(Spacer(1, 10))
            elements.append(Paragraph("Abstract:", styles['Heading3']))
            elements.append(Paragraph(article['abstract'], styles['Normal']))
        
        elements.append(Spacer(1, 20))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        }
    )

# Add dark mode preference endpoint
@router.post("/preferences/dark-mode")
async def set_dark_mode(enabled: bool, db_manager: DatabaseManager = Depends(get_db_manager)):
    db_manager.save_preference("dark_mode", enabled)
    return {"status": "success", "dark_mode": enabled}

# Add search history endpoints
@router.get("/search-history")
async def get_search_history(db_manager: DatabaseManager = Depends(get_db_manager)):
    history = db_manager.get_search_history()
    return {"status": "success", "history": history}

@router.post("/search-history/save")
async def save_search(search_params: Dict[str, Any], db_manager: DatabaseManager = Depends(get_db_manager)):
    search_id = db_manager.save_search(search_params)
    return {"status": "success", "search_id": search_id}

# Add article recommendations endpoint
@router.get("/recommendations")
async def get_recommendations(db_manager: DatabaseManager = Depends(get_db_manager)):
    # Get user's search history and generate recommendations
    history = db_manager.get_search_history()
    mesh_terms = db_manager.get_all_mesh_terms()
    
    # Simple recommendation based on most used MeSH terms
    recommended_articles = await search_pubmed_articles(
        search_params={
            "mesh_terms": [term["term"] for term in mesh_terms[:3]],
            "max_results": 5
        },
        email=db_manager.get_config("entrez_email"),
        api_key=db_manager.get_config("pubmed_api_key"),
        db_manager=db_manager
    )
    
    return {"status": "success", "recommendations": recommended_articles}

# Add collaboration endpoints
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.post("/collections/share")
async def share_collection(
    collection_id: str,
    shared_with_email: str,
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    # Share a collection with another user
    db_manager.share_collection(collection_id, shared_with_email)
    return {"status": "success", "message": "Collection shared successfully"}

# Add email notification scheduler
scheduler = BackgroundScheduler()
scheduler.start()

@router.post("/notifications/setup")
async def setup_notifications(
    search_params: Dict[str, Any],
    email: str,
    frequency: str,  # daily, weekly, monthly
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    # Save notification preferences
    notification_id = db_manager.save_notification_preferences(search_params, email, frequency)
    
    # Schedule the notification job
    scheduler.add_job(
        send_notification_email,
        trigger=frequency,
        args=[search_params, email],
        id=f"notification_{notification_id}"
    )
    
    return {"status": "success", "notification_id": notification_id}

# Add offline support endpoints
@router.post("/offline/save")
async def save_for_offline(
    article_ids: List[str],
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    # Save articles for offline access
    saved_articles = db_manager.save_articles_offline(article_ids)
    return {"status": "success", "saved_articles": saved_articles}

@router.get("/offline/articles")
async def get_offline_articles(db_manager: DatabaseManager = Depends(get_db_manager)):
    # Retrieve saved offline articles
    articles = db_manager.get_offline_articles()
    return {"status": "success", "articles": articles}