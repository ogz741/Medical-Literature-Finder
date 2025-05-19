import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Any, Optional
import re
from urllib.parse import quote_plus
import time

logger = logging.getLogger(__name__)

class RankingHandler:
    def __init__(self, db_manager=None, entrez_email: Optional[str] = None):
        self.db_manager = db_manager
        self.entrez_email = entrez_email
        if not logger.handlers:
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.ooir_base_url = "https://ooir.org/journals.php"

    def fetch_live_journal_rankings(self, specialty_query: str) -> List[Dict[str, Any]]:
        """
        Fetches journal rankings for a specialty live from ooir.org and sorts them by Impact Factor.
        Always fetches the latest live data from OOIR.org.
        """
        specialty_normalized = ' '.join(word.capitalize() for word in specialty_query.strip().split())
        logger.info(f"Fetching LIVE journal rankings for {specialty_normalized} from ooir.org.")

        rankings: List[Dict[str, Any]] = []
        
        try:
            specialty_url_encoded = quote_plus(specialty_normalized)
            # Construct URL for the JIF (Impact Factor) metric
            url = f"{self.ooir_base_url}?field=Clinical+Medicine&category={specialty_url_encoded}&metric=jif"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Connection': 'keep-alive'
            }
            
            # Add a small delay before making the request
            time.sleep(0.5) # Polite delay

            response = requests.get(url, headers=headers, timeout=25)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Find the table with journal rankings
            ranking_table = None
            all_tables = soup.find_all('table')
            for table in all_tables:
                header_row = table.find('tr')
                if header_row:
                    headers = [th.get_text(strip=True).lower() for th in header_row.find_all('th')]
                    if 'rank' in headers and 'journal' in headers and 'impact factor' in headers:
                        ranking_table = table
                        break
            
            if not ranking_table:
                logger.warning(f"Could not find a journal ranking table for {specialty_normalized} on {url}")
                return []

            rows = ranking_table.find_all('tr')[1:]  # Skip header row
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 3: # Need at least Rank, Journal, Impact Factor
                    rank_text = cols[0].get_text(strip=True)
                    journal_name_anchor = cols[1].find('a')
                    journal_name = journal_name_anchor.get_text(strip=True) if journal_name_anchor else cols[1].get_text(strip=True)
                    
                    impact_factor_text = cols[2].get_text(strip=True)
                    impact_factor = 0.0 # Default to 0.0

                    if impact_factor_text and impact_factor_text != '-':
                        # OOIR.org uses format like "ca.36.4" for impact factors
                        # We need to extract the numeric part after "ca."
                        match = re.search(r'ca\.?\s*(\d+\.?\d*)', impact_factor_text)
                        if match:
                            impact_factor_cleaned = match.group(1)
                            try:
                                impact_factor = float(impact_factor_cleaned)
                                logger.info(f"Parsed impact factor '{impact_factor_text}' to {impact_factor} for journal '{journal_name}'")
                            except ValueError:
                                logger.warning(f"Could not parse impact factor '{impact_factor_text}' for journal '{journal_name}'. Using 0.0.")
                        else:
                            # Try a more general approach as fallback
                            impact_factor_cleaned = re.sub(r'[^0-9.]', '', impact_factor_text)
                            if impact_factor_cleaned:
                                try:
                                    impact_factor = float(impact_factor_cleaned)
                                    logger.info(f"Fallback parsing of impact factor '{impact_factor_text}' to {impact_factor} for journal '{journal_name}'")
                                except ValueError:
                                    logger.warning(f"Could not parse impact factor '{impact_factor_text}' for journal '{journal_name}'. Using 0.0.")
                    
                    rankings.append({
                        "rank": rank_text if rank_text and rank_text != '-' else None,
                        "journal_name": journal_name,
                        "impact_factor": impact_factor,
                        "title": journal_name # For consistency if other parts of app use 'title'
                    })
            
            if not rankings:
                logger.warning(f"No journals parsed from the table for {specialty_normalized} on {url}")
            else:
                # Sort by impact factor in descending order
                rankings.sort(key=lambda x: x.get("impact_factor", 0.0), reverse=True)
                # Re-assign rank after sorting if ranks were missing or inconsistent
                for i, journal_data in enumerate(rankings):
                    journal_data["rank"] = i + 1

                logger.info(f"Successfully scraped and sorted {len(rankings)} journals for {specialty_normalized}.")

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {specialty_normalized}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error scraping rankings for {specialty_normalized}: {e}", exc_info=True)
        
        return rankings

    def get_journal_rankings(self, specialty: str, force_update: bool = True) -> List[Dict[str, Any]]:
        """
        Main method to get journal rankings for a specialty.
        Always fetches live data from OOIR.org.
        """
        # Always fetch live data regardless of force_update parameter
        return self.fetch_live_journal_rankings(specialty)

# Nothing else needed - this class now simply fetches journal rankings directly from OOIR.org