from Bio import Entrez
import logging
from typing import List, Dict, Any, Optional
from datetime import date, datetime
import asyncio # Retained for potential batching, but Entrez calls are blocking
import time

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Structure for an Article, similar to Pydantic model but as a type hint for now
ArticleDict = Dict[str, Any] # Keys: pubmed_id, title, journal, publication_date, authors, mesh_terms, abstract, url

class PubMedHandler:
    def __init__(self, email: str, api_key: Optional[str]):
        self.entrez_email = email
        self.pubmed_api_key = api_key
        Entrez.email = self.entrez_email
        if self.pubmed_api_key:
            Entrez.api_key = self.pubmed_api_key
        
        if not logger.handlers: # Ensure logger is configured
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def _get_entrez_sleep_time(self) -> float:
        """Returns the appropriate sleep time based on API key presence."""
        return 0.105 if self.pubmed_api_key else 0.4

    def _fetch_article_details_batch(self, pubmed_ids: List[str]) -> List[ArticleDict]:
        articles: List[ArticleDict] = []
        if not pubmed_ids:
            return articles

        try:
            batch_size = 100
            for i in range(0, len(pubmed_ids), batch_size):
                batch_ids = pubmed_ids[i:i+batch_size]
                logger.info(f"Fetching details for {len(batch_ids)} PubMed IDs (batch {i//batch_size + 1})...")
                
                # Ensure Entrez email and API key are set for this operation context
                Entrez.email = self.entrez_email
                if self.pubmed_api_key:
                    Entrez.api_key = self.pubmed_api_key
                else: # Explicitly clear if not set for this handler instance
                    Entrez.api_key = None 

                handle = Entrez.efetch(db="pubmed", id=batch_ids, retmode="xml")
                records = Entrez.read(handle)
                handle.close()
                
                for record in records.get("PubmedArticle", []):
                    article_data = record.get("MedlineCitation", {})
                    article_info = article_data.get("Article", {})
                    pmid_node = article_data.get("PMID")
                    pmid = str(pmid_node) if pmid_node else ""
                    if hasattr(pmid_node, 'version') and pmid_node.version: # Handle PMID version if present
                        pmid = f"{pmid}.{pmid_node.version}"

                    title_node = article_info.get("ArticleTitle", "No title available")
                    title = str(title_node) # Simplification, assuming string content
                    
                    journal_node = article_info.get("Journal", {})
                    journal_title = journal_node.get("Title", "N/A")
                    
                    pub_date_node = journal_node.get("JournalIssue", {}).get("PubDate", {})
                    publication_date_str = "Unknown"
                    year = pub_date_node.get("Year")
                    month = pub_date_node.get("Month", "Jan") # Default month for parsing
                    day = pub_date_node.get("Day", "01")    # Default day for parsing

                    if year:
                        try:
                            # Attempt to parse with known month formats or year only
                            if month.isdigit(): # e.g., "01" or "1"
                                month_val = int(month)
                                dt_obj = datetime(int(year), month_val, int(day) if day.isdigit() else 1)
                            else: # e.g., "Jan", "January"
                                dt_obj = datetime.strptime(f"{year}-{month}-{day}", "%Y-%b-%d")
                            publication_date_str = dt_obj.strftime("%Y-%m-%d")
                        except ValueError:
                            publication_date_str = f"{year}-{month if month else '??'}-{day if day else '??'}" # Fallback
                    elif pub_date_node.get("MedlineDate"):
                        publication_date_str = pub_date_node.get("MedlineDate")

                    authors_list = []
                    author_nodes = article_info.get("AuthorList", [])
                    for author in author_nodes if isinstance(author_nodes, list) else []:
                        if isinstance(author, dict):
                            last_name = author.get("LastName")
                            fore_name = author.get("ForeName")
                            initials = author.get("Initials")
                            if last_name: authors_list.append(f"{fore_name or initials or ''} {last_name}".strip())
                    
                    mesh_terms_list = []
                    mesh_heading_nodes = article_data.get("MeshHeadingList", [])
                    for mesh_node in mesh_heading_nodes if isinstance(mesh_heading_nodes, list) else []:
                        if isinstance(mesh_node, dict):
                            desc_name_node = mesh_node.get("DescriptorName")
                            if isinstance(desc_name_node, dict) and desc_name_node.get("#text"):
                                mesh_terms_list.append(desc_name_node.get("#text"))
                            elif isinstance(desc_name_node, str):
                                mesh_terms_list.append(desc_name_node)
                    
                    abstract_text = article_info.get("Abstract", {}).get("AbstractText", "No abstract available.")
                    if isinstance(abstract_text, list):
                        abstract_text = "\n".join(str(part) for part in abstract_text)
                    
                    articles.append({
                        "pubmed_id": pmid,
                        "title": title,
                        "journal": journal_title,
                        "publication_date": publication_date_str,
                        "authors": authors_list,
                        "mesh_terms": mesh_terms_list,
                        "abstract": str(abstract_text).strip(),
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
                        "impact_factor": 0.0  # Add default impact factor
                    })
                time.sleep(self._get_entrez_sleep_time())
        except Entrez.EntrezError as e:
            logger.error(f"Entrez API error during efetch: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error fetching article details: {e}", exc_info=True)
        return articles

    async def _search_one_journal(self, journal_name: str, start_date: date, end_date: date, max_results: int) -> List[str]:
        """Performs Entrez esearch for one journal, returns list of PubMed IDs."""
        Entrez.email = self.entrez_email # Ensure Entrez context is set
        if self.pubmed_api_key:
            Entrez.api_key = self.pubmed_api_key
        else:
            Entrez.api_key = None
            
        start_date_str = start_date.strftime("%Y/%m/%d")
        end_date_str = end_date.strftime("%Y/%m/%d")
        query = f'("{journal_name}"[Journal]) AND (("{start_date_str}"[Date - Publication] : "{end_date_str}"[Date - Publication]))'
        logger.info(f"PubMed query for {journal_name}: {query}")
        pubmed_ids = []
        try:
            handle = Entrez.esearch(db="pubmed", term=query, retmax=str(max_results), usehistory='y')
            search_results = Entrez.read(handle)
            handle.close()
            pubmed_ids = search_results.get("IdList", [])
            count = int(search_results.get("Count", 0))
            logger.info(f"Found {count} articles in {journal_name} (retrieved {len(pubmed_ids)} IDs).")
            time.sleep(self._get_entrez_sleep_time())
        except Entrez.EntrezError as e:
            logger.error(f"Entrez API error during esearch for {journal_name}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error in _search_one_journal for {journal_name}: {e}", exc_info=True)
        return pubmed_ids

    async def search_journals_and_fetch_details(
        self,
        journal_names: List[str],
        start_date: date,
        end_date: date,
        max_results_per_journal: int
    ) -> List[ArticleDict]:
        all_pubmed_ids: List[str] = []
        # If we want true concurrency, we'd use asyncio.gather with run_in_executor here.
        # For simplicity and to strictly respect NCBI limits sequentially for now:
        for journal_name in journal_names:
            ids = await self._search_one_journal(journal_name, start_date, end_date, max_results_per_journal)
            all_pubmed_ids.extend(ids)
            # Small delay even if _search_one_journal has one, to be safe between distinct esearch series
            await asyncio.sleep(self._get_entrez_sleep_time() * 0.5) 
        
        # Remove duplicates before fetching details
        unique_pubmed_ids = sorted(list(set(all_pubmed_ids)))
        logger.info(f"Total unique PubMed IDs to fetch details for: {len(unique_pubmed_ids)}")
        
        if not unique_pubmed_ids:
            return []

        # Fetching details can also be run in executor for large sets if needed
        detailed_articles = self._fetch_article_details_batch(unique_pubmed_ids)
        return detailed_articles

    def filter_articles_by_mesh(self, articles: List[ArticleDict], target_mesh_terms: List[str]) -> List[ArticleDict]:
        if not target_mesh_terms:
            return articles
        filtered_articles: List[ArticleDict] = []
        target_mesh_set = {term.lower() for term in target_mesh_terms}
        for article in articles:
            article_mesh_set = {term.lower() for term in article.get("mesh_terms", [])}
            if not target_mesh_set.isdisjoint(article_mesh_set):
                filtered_articles.append(article)
        logger.info(f"Filtered articles by MeSH: {len(articles)} -> {len(filtered_articles)} articles.")
        return filtered_articles

    def generate_demo_articles(
        self,
        top_journals_names: List[str],
        selected_mesh_terms_list: List[str],
        num_articles: int = 15 # Default number of articles for demo
    ) -> List[ArticleDict]:
        demo_articles: List[ArticleDict] = []
        if not top_journals_names:
            top_journals_names = ["Demo Journal Alpha", "Demo Journal Beta", "Demo Journal Charlie"]
        if not selected_mesh_terms_list:
            selected_mesh_terms_list = ["Education, Medical", "Simulation Training"]

        for i in range(num_articles):
            journal_idx = i % len(top_journals_names)
            mesh_count = min(1 + (i % 2), len(selected_mesh_terms_list))
            article_mesh_terms = selected_mesh_terms_list[:mesh_count]
            pmid_num = 10000000 + i 
            article: ArticleDict = {
                "pubmed_id": str(pmid_num),
                "title": f"Demo Study on {article_mesh_terms[0] if article_mesh_terms else 'Medical Topic'} - Vol. {i + 1}",
                "journal": top_journals_names[journal_idx],
                "publication_date": date(2023, (i % 12) + 1, (i % 28) + 1).strftime("%Y-%m-%d"),
                "authors": ["Dr. Demo One", "Dr. Demo Two"],
                "mesh_terms": article_mesh_terms,
                "abstract": f"This is a sample abstract for a demo article concerning {', '.join(article_mesh_terms) if article_mesh_terms else 'a general medical subject'}. This study explores various aspects and concludes with key findings. Demo abstract part {i + 1}.",
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid_num}/",
                "impact_factor": 0.0  # Add default impact factor
            }
            demo_articles.append(article)
        logger.info(f"Generated {len(demo_articles)} demo articles.")
        return demo_articles

# Add these helper functions at the module level
def search_pubmed_by_journal(entrez_email: str, pubmed_api_key: Optional[str], 
                             journal_name: str, start_date: date, end_date: date, 
                             max_results_per_journal: int) -> List[ArticleDict]:
    """Search PubMed for articles in a specific journal within a date range."""
    handler = PubMedHandler(email=entrez_email, api_key=pubmed_api_key)
    # Using asyncio.run to execute the coroutine in a synchronous context
    return asyncio.run(handler.search_journals_and_fetch_details(
        journal_names=[journal_name],
        start_date=start_date,
        end_date=end_date,
        max_results_per_journal=max_results_per_journal
    ))

def filter_articles_by_mesh(articles: List[ArticleDict], target_mesh_terms: List[str]) -> List[ArticleDict]:
    """Filter articles by MeSH terms. This is a module-level wrapper for the class method."""
    handler = PubMedHandler(email="temp@example.com", api_key=None)  # Temporary handler just to use the method
    return handler.filter_articles_by_mesh(articles, target_mesh_terms)

def generate_demo_articles(top_journals_names: List[str], selected_mesh_terms_list: List[str], 
                          num_articles: int = 15) -> List[ArticleDict]:
    """Generate demo articles. This is a module-level wrapper for the class method."""
    handler = PubMedHandler(email="temp@example.com", api_key=None)  # Temporary handler just to use the method
    return handler.generate_demo_articles(top_journals_names, selected_mesh_terms_list, num_articles)

async def search_pubmed_articles(search_params, email=None, api_key=None, db_manager=None) -> List[Dict[str, Any]]:
    """Search PubMed for articles matching the criteria"""
    logger.info(f"Searching PubMed with params: {search_params}")
    
    # Extract parameters
    mesh_terms = search_params.mesh_terms or []
    journal_specialty = search_params.journal_specialty
    start_date = search_params.start_date
    end_date = search_params.end_date
    
    # Create the PubMed handler
    handler = PubMedHandler(email=email, api_key=api_key)
    
    # Get journals to search, either from specific list or from rankings
    if search_params.selected_journals and len(search_params.selected_journals) > 0:
        journals_to_search = search_params.selected_journals
    else:
        # Return demo data if no email is provided
        if not email or email == "":
            logger.warning("No email provided for PubMed search. Using demo data.")
            demo_articles = handler.generate_demo_articles(
                top_journals_names=["Journal of Example Medicine", "Medical Example Quarterly"],
                selected_mesh_terms_list=mesh_terms,
                num_articles=10
            )
            
            # Attempt to get impact factors for demo journals
            if db_manager:
                try:
                    from .ranking_handler import RankingHandler
                    ranking_handler = RankingHandler(db_manager, email)
                    rankings = ranking_handler.get_journal_rankings(journal_specialty)
                    
                    # Create a mapping of journal names to impact factors
                    journal_impact_factors = {j["journal_name"].lower(): j["impact_factor"] for j in rankings}
                    
                    # Update impact factors in demo articles
                    for article in demo_articles:
                        journal_name = article["journal"].lower()
                        if journal_name in journal_impact_factors:
                            article["impact_factor"] = journal_impact_factors[journal_name]
                except Exception as e:
                    logger.warning(f"Error getting impact factors for demo articles: {e}")
            
            return demo_articles
        
        # Just use some default journals for now
        journals_to_search = ["Ophthalmology", "American Journal of Ophthalmology", "JAMA Ophthalmology"]
        # Limit to top journals
        max_journals = min(search_params.max_journals_to_search, len(journals_to_search))
        journals_to_search = journals_to_search[:max_journals]
    
    # Search journals and fetch article details
    all_articles = await handler.search_journals_and_fetch_details(
        journal_names=journals_to_search,
        start_date=start_date,
        end_date=end_date,
        max_results_per_journal=search_params.max_articles_per_journal
    )
    
    # Filter by MeSH terms if provided
    if mesh_terms:
        logger.info(f"Filtering {len(all_articles)} articles by MeSH terms: {mesh_terms}")
        all_articles = handler.filter_articles_by_mesh(all_articles, mesh_terms)
    
    # Add impact factors if possible
    if db_manager:
        try:
            from .ranking_handler import RankingHandler
            ranking_handler = RankingHandler(db_manager, email)
            rankings = ranking_handler.get_journal_rankings(journal_specialty)
            
            # Create a mapping of journal names to impact factors
            journal_impact_factors = {j["journal_name"].lower(): j["impact_factor"] for j in rankings}
            
            # Update impact factors in articles
            for article in all_articles:
                journal_name = article["journal"].lower()
                if journal_name in journal_impact_factors:
                    article["impact_factor"] = journal_impact_factors[journal_name]
        except Exception as e:
            logger.warning(f"Error getting impact factors for articles: {e}")
    
    logger.info(f"Search complete. Returning {len(all_articles)} articles.")
    return all_articles

# Add a new function to handle PubMed search requests for the API endpoint
async def search_pubmed(
    query: str, 
    page: int = 1, 
    per_page: int = 10, 
    sort: Optional[str] = None,
    filter_date_start: Optional[str] = None,
    filter_date_end: Optional[str] = None,
    journal_filter: Optional[List[str]] = None,
    mesh_terms_filter: Optional[List[str]] = None, # New parameter for MeSH terms
    entrez_email: str = "temp@example.com",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search PubMed for articles matching the query and filters.
    
    Args:
        query: The search query
        page: Page number (1-based)
        per_page: Results per page
        sort: Sorting method (relevance, date, etc.)
        filter_date_start: Start date for filtering (YYYY-MM-DD)
        filter_date_end: End date for filtering (YYYY-MM-DD)
        journal_filter: List of journal names to filter by
        mesh_terms_filter: List of MeSH terms to filter by (user selected)
        entrez_email: Email for NCBI Entrez API
        api_key: API key for NCBI Entrez API
        
    Returns:
        Dict with search results including page info and articles
    """
    logger.info(f"Searching PubMed with query: {query}, page: {page}, per_page: {per_page}, journals: {journal_filter}, mesh_terms: {mesh_terms_filter}")
    
    # Initialize handler
    handler = PubMedHandler(email=entrez_email, api_key=api_key)
    
    # Build the PubMed query
    pubmed_query_parts = []
    if query and query.strip():
        pubmed_query_parts.append(f"({query.strip()})")
    
    # Add date filters if provided
    if filter_date_start or filter_date_end:
        date_start = filter_date_start or "1900/01/01"
        date_end = filter_date_end or datetime.now().strftime("%Y/%m/%d")
        # Ensure date format is YYYY/MM/DD for Entrez
        try:
            if filter_date_start: date_start = datetime.strptime(date_start, '%Y-%m-%d').strftime('%Y/%m/%d')
            if filter_date_end: date_end = datetime.strptime(date_end, '%Y-%m-%d').strftime('%Y/%m/%d')
        except ValueError:
            logger.warning(f"Invalid date format for PubMed search. Using defaults. Start: {filter_date_start}, End: {filter_date_end}")
            date_start = "1900/01/01"
            date_end = datetime.now().strftime("%Y/%m/%d")
            
        date_filter = f'("{date_start}"[Date - Publication] : "{date_end}"[Date - Publication])'
        pubmed_query_parts.append(date_filter)
    
    # Add journal filter if provided
    if journal_filter and len(journal_filter) > 0:
        journal_terms = " OR ".join([f'"{journal}"[Journal]' for journal in journal_filter])
        journal_filter_query = f"({journal_terms})"
        pubmed_query_parts.append(journal_filter_query)

    # Add MeSH terms filter if provided
    if mesh_terms_filter and len(mesh_terms_filter) > 0:
        mesh_query_terms = " OR ".join([f'"{term}"[MeSH Major Topic]' for term in mesh_terms_filter])
        mesh_filter_query = f"({mesh_query_terms})"
        pubmed_query_parts.append(mesh_filter_query)
    
    if not pubmed_query_parts: # if query was empty and no other filters, this might happen
        logger.warning("PubMed search query is empty after processing all parts.")
        return {
            "total": 0,
            "page": page,
            "per_page": per_page,
            "pages": 0,
            "articles": []
        }

    pubmed_query = " AND ".join(pubmed_query_parts)
    logger.info(f"Constructed PubMed Query: {pubmed_query}")

    # Set up Entrez
    Entrez.email = entrez_email
    if api_key:
        Entrez.api_key = api_key
    
    try:
        # Calculate indices for pagination
        start = (page - 1) * per_page
        
        # Search PubMed
        handle = Entrez.esearch(
            db="pubmed", 
            term=pubmed_query, 
            retstart=start,
            retmax=per_page,
            sort=sort if sort else None
        )
        search_results = Entrez.read(handle)
        handle.close()
        
        total_results = int(search_results.get("Count", 0))
        pubmed_ids = search_results.get("IdList", [])
        
        # Fetch article details if we have any results
        articles = []
        if pubmed_ids:
            articles = handler._fetch_article_details_batch(pubmed_ids)
            
        # Sort articles if needed
        if sort == "date":
            articles.sort(key=lambda x: x.get("publication_date", ""), reverse=True)
            
        # Return results with pagination info
        return {
            "total": total_results,
            "page": page,
            "per_page": per_page,
            "pages": (total_results + per_page - 1) // per_page,  # Ceiling division
            "articles": articles
        }
        
    except Exception as e:
        logger.error(f"Error searching PubMed: {e}", exc_info=True)
        return {
            "total": 0,
            "page": page,
            "per_page": per_page,
            "pages": 0,
            "articles": []
        }

MAX_DOWNLOAD_RESULTS = 500 # Configurable maximum number of articles for download to prevent abuse

async def search_pubmed_for_download(
    query: str,
    journal_filter: Optional[List[str]] = None,
    mesh_terms_filter: Optional[List[str]] = None,
    filter_date_start: Optional[str] = None,
    filter_date_end: Optional[str] = None,
    entrez_email: str = "temp@example.com",
    api_key: Optional[str] = None,
    max_results: int = MAX_DOWNLOAD_RESULTS
) -> List[ArticleDict]:
    """
    Search PubMed for articles matching the criteria, optimized for downloading all results up to a limit.
    """
    logger.info(f"PubMed download search: Q='{query}', J='{journal_filter}', M='{mesh_terms_filter}', Max='{max_results}'")
    handler = PubMedHandler(email=entrez_email, api_key=api_key)

    pubmed_query_parts = []
    if query and query.strip():
        pubmed_query_parts.append(f"({query.strip()})")

    if filter_date_start or filter_date_end:
        date_start = filter_date_start or "1900/01/01"
        date_end = filter_date_end or datetime.now().strftime("%Y/%m/%d")
        try:
            if filter_date_start: date_start = datetime.strptime(date_start, '%Y-%m-%d').strftime('%Y/%m/%d')
            if filter_date_end: date_end = datetime.strptime(date_end, '%Y-%m-%d').strftime('%Y/%m/%d')
        except ValueError:
            logger.warning(f"Invalid date format for PubMed download search. Start: {filter_date_start}, End: {filter_date_end}")
            date_start = "1900/01/01"
            date_end = datetime.now().strftime("%Y/%m/%d")
        date_filter = f'("{date_start}"[Date - Publication] : "{date_end}"[Date - Publication])'
        pubmed_query_parts.append(date_filter)

    if journal_filter and len(journal_filter) > 0:
        journal_terms = " OR ".join([f'"{journal}"[Journal]' for journal in journal_filter])
        pubmed_query_parts.append(f"({journal_terms})")

    if mesh_terms_filter and len(mesh_terms_filter) > 0:
        mesh_terms = " OR ".join([f'"{term}"[MeSH Major Topic]' for term in mesh_terms_filter])
        pubmed_query_parts.append(f"({mesh_terms})")

    if not pubmed_query_parts:
        logger.warning("PubMed download search query is empty.")
        return []

    final_query = " AND ".join(pubmed_query_parts)
    logger.info(f"Constructed PubMed Download Query: {final_query}")

    Entrez.email = entrez_email
    if api_key:
        Entrez.api_key = api_key
    
    all_articles: List[ArticleDict] = []
    retrieved_ids = set()

    # NCBI recommends not using usehistory=y for very large queries that will be chunked.
    # We will fetch IDs in one go up to max_results, then fetch details.
    # If max_results > 10000, we might need to chunk esearch too, but Entrez recommends against it for stability.
    # For now, assume max_results is within a reasonable single esearch limit (e.g., up to 10k, though pubmed might cap lower).

    try:
        logger.info(f"Performing esearch for download with retmax={max_results}")
        handle = Entrez.esearch(db="pubmed", term=final_query, retmax=str(max_results), sort="relevance") # or sort by date, etc.
        search_results = Entrez.read(handle)
        handle.close()
        time.sleep(handler._get_entrez_sleep_time()) # Respect rate limits after esearch

        pubmed_ids = search_results.get("IdList", [])
        logger.info(f"esearch for download found {len(pubmed_ids)} IDs (total reported: {search_results.get('Count', 'N/A')}).")

        if pubmed_ids:
            # Fetch details in batches using existing handler method
            # _fetch_article_details_batch already handles its own rate limiting for efetch calls
            all_articles = handler._fetch_article_details_batch(pubmed_ids)
            logger.info(f"Fetched details for {len(all_articles)} articles for download.")

    except Entrez.EntrezError as e:
        logger.error(f"Entrez API error during download search (esearch/efetch): {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error during PubMed download search: {e}", exc_info=True)
    
    return all_articles

async def fetch_article_details_by_pmid(pmid: str, entrez_email: str, api_key: Optional[str]) -> Optional[ArticleDict]:
    """Fetches details for a single PubMed ID."""
    logger.info(f"Fetching details for single PMID: {pmid}")
    handler = PubMedHandler(email=entrez_email, api_key=api_key)
    
    # _fetch_article_details_batch expects a list and returns a list
    articles = handler._fetch_article_details_batch([pmid])
    if articles:
        logger.info(f"Successfully fetched details for PMID: {pmid}")
        return articles[0]
    else:
        logger.warning(f"Could not fetch details for PMID: {pmid}")
        return None

if __name__ == '__main__':
    # --- IMPORTANT: For direct testing, set your Entrez email and API key below ---
    # --- (Or ensure they are configured via a DatabaseManager if you adapt this test) ---
    TEST_ENTREZ_EMAIL = "your.email@example.com"  # <--- REPLACE THIS
    TEST_PUBMED_API_KEY = None                    # <--- REPLACE WITH YOUR KEY or None

    if TEST_ENTREZ_EMAIL == "your.email@example.com":
        print("\nWARNING: Please set your TEST_ENTREZ_EMAIL in pubmed_handler.py for testing.")
        # exit()

    print("--- Testing PubMed Article Search ---")
    journal_to_search = "Ophthalmology" # A common, high-volume journal for testing
    test_start_date = date(2023, 1, 1)
    test_end_date = date(2023, 1, 31)
    
    print(f"Searching {journal_to_search} from {test_start_date} to {test_end_date}...")
    articles_from_journal = search_pubmed_by_journal(
        entrez_email=TEST_ENTREZ_EMAIL,
        pubmed_api_key=TEST_PUBMED_API_KEY,
        journal_name=journal_to_search,
        start_date=test_start_date,
        end_date=test_end_date,
        max_results_per_journal=5 # Keep low for testing
    )

    if articles_from_journal:
        print(f"\n--- Found {len(articles_from_journal)} articles from {journal_to_search} ---")
        for i, art in enumerate(articles_from_journal[:2]): # Print first 2
            print(f"  Article {i+1}:")
            print(f"    PMID: {art.get('pubmed_id')}")
            print(f"    Title: {art.get('title')}")
            print(f"    Journal: {art.get('journal')}")
            print(f"    Date: {art.get('publication_date')}")
            print(f"    Authors: {', '.join(art.get('authors', []))}")
            print(f"    MeSH: {', '.join(art.get('mesh_terms', []))}")
            print(f"    Abstract: {art.get('abstract', '')[:100]}...") # First 100 chars
            print(f"    URL: {art.get('url')}")
    else:
        print(f"No articles found for {journal_to_search} in the date range.")

    # --- Test MeSH Filtering ---
    if articles_from_journal:
        sample_mesh_targets = ["Cataract Extraction", "Humans", "Aged"] # Example MeSH terms that might appear
        print(f"\n--- Filtering {len(articles_from_journal)} articles by MeSH terms: {sample_mesh_targets} ---")
        filtered = filter_articles_by_mesh(articles_from_journal, sample_mesh_targets)
        print(f"Found {len(filtered)} articles after MeSH filtering.")
        for i, art in enumerate(filtered[:2]): # Print first 2 filtered
            print(f"  Filtered Article {i+1}: {art.get('title')}")
            print(f"    Matched MeSH: {[t for t in art.get('mesh_terms', []) if t.lower() in [mt.lower() for mt in sample_mesh_targets]]}")

    # --- Test Demo Article Generation ---
    print("\n--- Generating Demo Articles ---")
    demo_journals = ["Awesome Journal of Demos", "Journal of Mock Data"]
    demo_mesh = ["Medical Education", "Simulation"] 
    generated_demos = generate_demo_articles(demo_journals, demo_mesh, num_articles=3)
    for i, art in enumerate(generated_demos):
        print(f"  Demo Article {i+1}: {art.get('title')} in {art.get('journal')}")
        print(f"    MeSH: {art.get('mesh_terms')}") 