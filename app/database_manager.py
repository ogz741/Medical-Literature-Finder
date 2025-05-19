import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, date
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Default MeSH terms for medical education
DEFAULT_MESH_TERMS = [
    "Education, Medical", "Education, Medical, Graduate", "Education, Medical, Undergraduate",
    "Education, Medical, Continuing", "Internship and Residency", "Clinical Competence",
    "Curriculum", "Competency-Based Education", "Teaching",
    "Educational Measurement", "Schools, Medical", "Simulation Training", "Patient Simulation",
    "Problem-Based Learning", "Teaching Materials", "Faculty, Medical", "Mentors",
    "Educational Technology", "Program Development", "Program Evaluation", "Certification",
    "Attitude of Health Personnel", "Specialty Boards", "Fellowships and Scholarships"
]

class DatabaseManager:
    """
    JSON-based storage manager that replaces the SQLite database.
    All data is stored in JSON files in a data directory.
    """
    def __init__(self, data_dir: str = None):
        """
        Initialize the database manager with a data directory.
        
        Args:
            data_dir: Directory to store JSON data files. If None, uses default in app directory.
        """
        if data_dir is None:
            # Use default in the application directory
            data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        
        self.data_dir = data_dir
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Create subdirectories for different data types
        self.mesh_terms_dir = os.path.join(self.data_dir, 'mesh_terms')
        self.journal_rankings_dir = os.path.join(self.data_dir, 'journal_rankings')
        self.pubmed_cache_dir = os.path.join(self.data_dir, 'pubmed_cache')
        self.config_dir = os.path.join(self.data_dir, 'config')
        self.search_history_dir = os.path.join(self.data_dir, 'search_history')
        self.bookmarks_dir = os.path.join(self.data_dir, 'bookmarks')
        self.preferences_dir = os.path.join(self.data_dir, 'preferences')
        
        # Create all subdirectories
        for dir_path in [self.mesh_terms_dir, self.journal_rankings_dir, self.pubmed_cache_dir,
                         self.config_dir, self.search_history_dir, self.bookmarks_dir, 
                         self.preferences_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        # Initialize with default data
        self.initialize_default_mesh_terms()
        
        # Set up default API key and email if not configured
        if not self.get_config("entrez_email"):
            self.save_config("entrez_email", "your.email@example.com")
        if not self.get_config("pubmed_api_key"):
            self.save_config("pubmed_api_key", "")

    # --- Utility Functions ---
    def _read_json_file(self, file_path: str) -> Any:
        """Read and parse a JSON file."""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as file:
                    return json.load(file)
            return None
        except Exception as e:
            logging.error(f"Error reading JSON file {file_path}: {e}")
            return None

    def _write_json_file(self, file_path: str, data: Any) -> bool:
        """Write data to a JSON file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logging.error(f"Error writing JSON file {file_path}: {e}")
            return False
    
    def _get_all_files(self, directory: str, extension: str = '.json') -> List[str]:
        """Get all files with a specific extension in a directory."""
        try:
            return [f for f in os.listdir(directory) if f.endswith(extension)]
        except Exception as e:
            logging.error(f"Error listing files in {directory}: {e}")
            return []

    # --- PubMed Cache Functions ---
    def cache_pubmed_results(self, search_query: str, results: dict) -> bool:
        """Cache PubMed search results"""
        try:
            # Create a safe filename from the search query
            safe_filename = "".join(c if c.isalnum() else "_" for c in search_query)
            safe_filename = f"{safe_filename[:100]}.json"  # Limit length
            
            file_path = os.path.join(self.pubmed_cache_dir, safe_filename)
            
            # Add timestamp to results
            data = {
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
            
            return self._write_json_file(file_path, data)
        except Exception as e:
            logging.error(f"Error caching PubMed results: {e}")
            return False

    def get_cached_pubmed_results(self, search_query: str) -> Optional[dict]:
        """Get cached PubMed search results if they exist"""
        try:
            # Create a safe filename from the search query
            safe_filename = "".join(c if c.isalnum() else "_" for c in search_query)
            safe_filename = f"{safe_filename[:100]}.json"  # Limit length
            
            file_path = os.path.join(self.pubmed_cache_dir, safe_filename)
            
            return self._read_json_file(file_path)
        except Exception as e:
            logging.error(f"Error getting cached PubMed results: {e}")
            return None

    # --- Journal Rankings Functions ---
    def cache_journal_rankings(self, specialty: str, rankings: List[Dict[str, Any]], date: str = None) -> bool:
        """Cache journal rankings for a specialty and date"""
        if date is None:
            date = "latest"  # Use "latest" as a placeholder when no date is specified
            
        try:
            # Create a safe filename from the specialty and date
            safe_specialty = "".join(c if c.isalnum() else "_" for c in specialty.lower())
            safe_date = "".join(c if c.isalnum() else "_" for c in date)
            
            filename = f"{safe_specialty}_{safe_date}.json"
            file_path = os.path.join(self.journal_rankings_dir, filename)
            
            # Add timestamp to rankings
            data = {
                "specialty": specialty,
                "date": date,
                "rankings": rankings,
                "timestamp": datetime.now().isoformat()
            }
            
            result = self._write_json_file(file_path, data)
            logging.info(f"Cached {len(rankings)} journal rankings for {specialty} (date: {date})")
            return result
        except Exception as e:
            logging.error(f"Error caching journal rankings: {e}")
            return False

    def get_cached_journal_rankings(self, specialty: str, date: str = None) -> Optional[List[Dict[str, Any]]]:
        """Get cached journal rankings for a specialty and date if they exist"""
        if date is None:
            date = "latest"  # Use "latest" as a placeholder when no date is specified
            
        try:
            # Create a safe filename from the specialty and date
            safe_specialty = "".join(c if c.isalnum() else "_" for c in specialty.lower())
            safe_date = "".join(c if c.isalnum() else "_" for c in date)
            
            filename = f"{safe_specialty}_{safe_date}.json"
            file_path = os.path.join(self.journal_rankings_dir, filename)
            
            data = self._read_json_file(file_path)
            
            if data:
                logging.info(f"Retrieved {len(data['rankings'])} cached journal rankings for {specialty} (date: {date})")
                return data["rankings"]
            
            # If not found with the specific date, try the "latest" placeholder
            if date != "latest":
                latest_filename = f"{safe_specialty}_latest.json"
                latest_file_path = os.path.join(self.journal_rankings_dir, latest_filename)
                
                latest_data = self._read_json_file(latest_file_path)
                
                if latest_data:
                    logging.info(f"Retrieved {len(latest_data['rankings'])} cached journal rankings for {specialty} (using 'latest' fallback)")
                    return latest_data["rankings"]
            
            return None
        except Exception as e:
            logging.error(f"Error getting cached journal rankings: {e}")
            return None

    def get_available_specialties(self) -> List[str]:
        """Get a list of all specialties that have cached rankings"""
        try:
            specialties = set()
            
            for filename in self._get_all_files(self.journal_rankings_dir):
                data = self._read_json_file(os.path.join(self.journal_rankings_dir, filename))
                if data and "specialty" in data:
                    specialties.add(data["specialty"])
            
            return sorted(list(specialties))
        except Exception as e:
            logging.error(f"Error getting available specialties: {e}")
            return []

    def get_available_dates_for_specialty(self, specialty: str) -> List[str]:
        """Get a list of all dates available for a specialty"""
        try:
            dates = set()
            safe_specialty = "".join(c if c.isalnum() else "_" for c in specialty.lower())
            
            for filename in self._get_all_files(self.journal_rankings_dir):
                if filename.startswith(f"{safe_specialty}_"):
                    data = self._read_json_file(os.path.join(self.journal_rankings_dir, filename))
                    if data and "date" in data:
                        dates.add(data["date"])
            
            # Sort dates in descending order
            return sorted(list(dates), reverse=True)
        except Exception as e:
            logging.error(f"Error getting available dates for specialty: {e}")
            return []

    # --- Search History Functions ---
    def add_to_search_history(self, query: str, result_count: int = 0) -> bool:
        """Add a search to the search history"""
        try:
            # Create a new entry
            entry = {
                "id": datetime.now().timestamp(),  # Use timestamp as ID
                "query": query,
                "result_count": result_count,
                "timestamp": datetime.now().isoformat()
            }
            
            # Load existing history
            history_file = os.path.join(self.search_history_dir, "search_history.json")
            history = self._read_json_file(history_file) or []
            
            # Add new entry
            history.append(entry)
            
            # Save history
            return self._write_json_file(history_file, history)
        except Exception as e:
            logging.error(f"Error adding to search history: {e}")
            return False

    def get_search_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent search history"""
        try:
            # Load existing history
            history_file = os.path.join(self.search_history_dir, "search_history.json")
            history = self._read_json_file(history_file) or []
            
            # Sort by timestamp (newest first) and limit
            history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            return history[:limit]
        except Exception as e:
            logging.error(f"Error getting search history: {e}")
            return []

    # --- Cache Management Functions ---
    def clear_cache(self, cache_type: str = 'all') -> bool:
        """
        Clear the cache based on type:
        - 'pubmed': Clear only PubMed search cache
        - 'rankings': Clear only journal rankings cache
        - 'all': Clear all caches
        """
        try:
            if cache_type in ('pubmed', 'all'):
                for file in self._get_all_files(self.pubmed_cache_dir):
                    os.remove(os.path.join(self.pubmed_cache_dir, file))
                logging.info("Cleared PubMed cache")
                
            if cache_type in ('rankings', 'all'):
                for file in self._get_all_files(self.journal_rankings_dir):
                    os.remove(os.path.join(self.journal_rankings_dir, file))
                logging.info("Cleared journal rankings cache")
                
            return True
        except Exception as e:
            logging.error(f"Error clearing cache: {e}")
            return False

    # --- User Preferences Functions ---
    def save_preference(self, key: str, value: Any) -> bool:
        """Save a user preference"""
        try:
            # Create a safe filename from the key
            safe_key = "".join(c if c.isalnum() else "_" for c in key)
            file_path = os.path.join(self.preferences_dir, f"{safe_key}.json")
            
            data = {
                "key": key,
                "value": value
            }
            
            return self._write_json_file(file_path, data)
        except Exception as e:
            logging.error(f"Error saving preference: {e}")
            return False

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference or return default if not found"""
        try:
            # Create a safe filename from the key
            safe_key = "".join(c if c.isalnum() else "_" for c in key)
            file_path = os.path.join(self.preferences_dir, f"{safe_key}.json")
            
            data = self._read_json_file(file_path)
            
            if data:
                return data.get("value", default)
            
            # If the preference doesn't exist, save the default
            if default is not None:
                self.save_preference(key, default)
                
            return default
        except Exception as e:
            logging.error(f"Error getting preference: {e}")
            return default

    # --- Article Bookmarks Functions ---
    def bookmark_article(self, pmid: str, title: str, authors: str, journal: str, 
                        pub_date: str, abstract: str) -> bool:
        """Add an article to bookmarks"""
        try:
            # Create a bookmark entry
            bookmark = {
                "pmid": pmid,
                "title": title,
                "authors": authors,
                "journal": journal,
                "pub_date": pub_date,
                "abstract": abstract,
                "timestamp": datetime.now().isoformat()
            }
            
            # Save the bookmark to a file using pmid as the filename
            file_path = os.path.join(self.bookmarks_dir, f"{pmid}.json")
            
            return self._write_json_file(file_path, bookmark)
        except Exception as e:
            logging.error(f"Error bookmarking article: {e}")
            return False

    def get_bookmarked_articles(self) -> List[Dict[str, Any]]:
        """Get all bookmarked articles"""
        try:
            bookmarks = []
            
            for file in self._get_all_files(self.bookmarks_dir):
                file_path = os.path.join(self.bookmarks_dir, file)
                bookmark = self._read_json_file(file_path)
                if bookmark:
                    bookmarks.append(bookmark)
            
            # Sort by timestamp (newest first)
            bookmarks.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            return bookmarks
        except Exception as e:
            logging.error(f"Error getting bookmarked articles: {e}")
            return []

    def remove_article_bookmark(self, pmid: str) -> bool:
        """Remove an article from bookmarks"""
        try:
            file_path = os.path.join(self.bookmarks_dir, f"{pmid}.json")
            
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            
            return False
        except Exception as e:
            logging.error(f"Error removing article bookmark: {e}")
            return False

    # --- Config Management Functions ---
    def save_config(self, key: str, value: str) -> bool:
        """Save a config value"""
        try:
            # Create a safe filename from the key
            safe_key = "".join(c if c.isalnum() else "_" for c in key)
            file_path = os.path.join(self.config_dir, f"{safe_key}.json")
            
            data = {
                "key": key,
                "value": value
            }
            
            result = self._write_json_file(file_path, data)
            logging.info(f"Config saved: {key}")
            return result
        except Exception as e:
            logging.error(f"Error saving config {key}: {e}")
            return False

    def get_config(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a config value or return default if not found"""
        try:
            # Create a safe filename from the key
            safe_key = "".join(c if c.isalnum() else "_" for c in key)
            file_path = os.path.join(self.config_dir, f"{safe_key}.json")
            
            data = self._read_json_file(file_path)
            
            if data:
                return data.get("value")
            
            # If the config doesn't exist, save the default
            if default is not None:
                self.save_config(key, default)
                
            return default
        except Exception as e:
            logging.error(f"Error getting config {key}: {e}")
            return default

    # --- MeSH Term Management Functions ---
    def initialize_default_mesh_terms(self):
        """Initialize default MeSH terms if none exist"""
        try:
            # Check if mesh terms directory is empty
            if not self._get_all_files(self.mesh_terms_dir):
                for term in DEFAULT_MESH_TERMS:
                    self.add_mesh_term(term)
                logging.info(f"Initialized {len(DEFAULT_MESH_TERMS)} default MeSH terms.")
        except Exception as e:
            logging.error(f"Error initializing default MeSH terms: {e}")

    def add_mesh_term(self, term: str) -> Optional[str]:
        """Add a MeSH term and return its ID"""
        try:
            # Generate a simple ID based on the term
            term_id = f"MESH_{hash(term) % 10000:04d}"
            
            # Check if term already exists
            for existing_file in self._get_all_files(self.mesh_terms_dir):
                existing_path = os.path.join(self.mesh_terms_dir, existing_file)
                existing_data = self._read_json_file(existing_path)
                
                if existing_data and existing_data.get("term") == term:
                    logging.warning(f"MeSH term '{term}' already exists.")
                    return existing_data.get("id")
            
            # Create a new term
            file_path = os.path.join(self.mesh_terms_dir, f"{term_id}.json")
            
            data = {
                "id": term_id,
                "term": term,
                "tree_number": None,
                "parent_id": None,
                "is_major": 0
            }
            
            self._write_json_file(file_path, data)
            logging.info(f"MeSH term added: {term}")
            
            return term_id
        except Exception as e:
            logging.error(f"Error adding MeSH term {term}: {e}")
            return None

    def get_all_mesh_terms(self) -> List[Dict[str, Any]]:
        """Get all MeSH terms"""
        try:
            terms = []
            
            for file in self._get_all_files(self.mesh_terms_dir):
                file_path = os.path.join(self.mesh_terms_dir, file)
                term_data = self._read_json_file(file_path)
                
                if term_data:
                    terms.append({
                        "id": term_data.get("id"),
                        "term": term_data.get("term")
                    })
            
            # Sort by term alphabetically
            terms.sort(key=lambda x: x.get("term", ""))
            
            return terms
        except Exception as e:
            logging.error(f"Error getting all MeSH terms: {e}")
            return []

    def get_mesh_term_by_name(self, term_name: str) -> Optional[Dict[str, Any]]:
        """Fetches a MeSH term by its name."""
        try:
            for file in self._get_all_files(self.mesh_terms_dir):
                file_path = os.path.join(self.mesh_terms_dir, file)
                term_data = self._read_json_file(file_path)
                
                if term_data and term_data.get("term") == term_name:
                    return {
                        "id": term_data.get("id"),
                        "term": term_data.get("term")
                    }
            
            return None
        except Exception as e:
            logging.error(f"Error getting MeSH term by name '{term_name}': {e}")
            return None

    def delete_mesh_term(self, term_id: str) -> bool:
        """Delete a MeSH term by its ID"""
        try:
            for file in self._get_all_files(self.mesh_terms_dir):
                file_path = os.path.join(self.mesh_terms_dir, file)
                term_data = self._read_json_file(file_path)
                
                if term_data and term_data.get("id") == term_id:
                    os.remove(file_path)
                    logging.info(f"MeSH term with id {term_id} deleted.")
                    return True
            
            logging.warning(f"No MeSH term found with id {term_id} to delete.")
            return False
        except Exception as e:
            logging.error(f"Error deleting MeSH term with id {term_id}: {e}")
            return False

    def get_app_config_model(self) -> Dict[str, Optional[str]]:
        """Returns the app configuration as a dictionary."""
        return {
            "entrez_email": self.get_config("entrez_email"),
            "pubmed_api_key": self.get_config("pubmed_api_key")
        }
        
    # --- Data Migration Function (For Transitioning from SQLite) ---
    def migrate_from_sqlite(self, sqlite_db_path: str) -> bool:
        """
        IMPORTANT: This function is a placeholder and should be implemented
        if you need to migrate data from SQLite to JSON storage.
        
        1. This would require the sqlite3 module
        2. You would need to read from the SQLite DB and write to JSON files
        3. For a production app, this would be more complex with error handling
        
        Since we're starting fresh with JSON storage, this isn't implemented.
        """
        logging.warning("SQLite migration is not implemented. Starting fresh with JSON storage.")
        return True 