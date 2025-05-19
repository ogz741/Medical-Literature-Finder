"""
Impact factors for medical journals by specialty.
This data is sourced from online journal ranking databases like OOIR.org.

For specialties that don't have hard-coded data, we use dynamic lookup
and fallback to estimated values based on journal name patterns.
"""

import re
from typing import Dict, List, Any, Optional

# Mapping of journal names to their impact factors by specialty
JOURNAL_IMPACT_FACTORS = {
    "Allergy": {
        "Allergy": 12.6,
        "Journal of Allergy and Clinical Immunology": 11.4,
        "Clinical Reviews in Allergy & Immunology": 8.4,
        "Journal of Allergy and Clinical Immunology-In Practice": 8.2,
        "Clinical and Experimental Allergy": 6.3,
        "Allergology International": 6.2,
        "Journal of Investigational Allergology and Clinical Immunology": 6.1,
        "Annals of Allergy Asthma & Immunology": 5.8,
        "Current Allergy and Asthma Reports": 5.4,
        "Contact Dermatitis": 4.8,
        "Clinical and Translational Allergy": 4.6,
        "Pediatric Allergy and Immunology": 4.3,
        "Allergy Asthma & Immunology Research": 4.1,
        "World Allergy Organization Journal": 3.9,
        "Journal of Asthma and Allergy": 3.7,
        "Current Opinion in Allergy and Clinical Immunology": 3.0,
        "Immunology and Allergy Clinics of North America": 2.7,
        "Allergy Asthma and Clinical Immunology": 2.6,
        "Allergy and Asthma Proceedings": 2.6,
        "Allergologia et Immunopathologia": 2.5,
        "International Archives of Allergy and Immunology": 2.5,
        "Asian Pacific Journal of Allergy and Immunology": 2.3,
        "Journal of Asthma": 1.7,
        "Allergologie": 1.4,
        "Postepy Dermatologii i Alergologii": 1.4,
        "Iranian Journal of Allergy Asthma and Immunology": 1.2,
        "Pediatric Allergy Immunology and Pulmonology": 1.1,
        "Revue Francaise d'Allergologie": 0.5,
    },
    "Ophthalmology": {
        "Progress in Retinal and Eye Research": 14.7,
        "Ophthalmology": 9.2,
        "JAMA Ophthalmology": 7.9,
        "Ocular Surface": 7.5,
        "Survey of Ophthalmology": 5.9,
        "Annual Review of Vision Science": 5.5,
        "Clinical and Experimental Ophthalmology": 3.8,
        "American Journal of Ophthalmology": 5.6,
        "Contact Lens & Anterior Eye": 3.2,
        "British Journal of Ophthalmology": 4.6,
        "Asia-Pacific Journal of Ophthalmology": 2.8,
        "Canadian Journal of Ophthalmology-Journal Canadien d'Ophtalmologie": 2.5,
        "Acta Ophthalmologica": 3.5,
        "Experimental Eye Research": 3.5,
        "Current Opinion in Ophthalmology": 3.1,
        "Journal of Refractive Surgery": 2.9,
        "Eye": 2.8,
        "Ophthalmic and Physiological Optics": 2.7,
        "Translational Vision Science & Technology": 2.5,
        "Ophthalmology and Therapy": 2.4,
        "Journal of Cataract and Refractive Surgery": 4.1,
        "Documenta Ophthalmologica": 2.0,
        "Ocular Immunology and Inflammation": 2.2,
        "Graefes Archive for Clinical and Experimental Ophthalmology": 3.3,
        "Retina-The Journal of Retinal and Vitreous Diseases": 4.3,
        "Indian Journal of Ophthalmology": 1.8,
        "Ophthalmologica": 2.2,
        "Japanese Journal of Ophthalmology": 1.9,
        "Eye & Contact Lens-Science and Clinical Practice": 2.3,
        "Journal of Vision": 2.1,
        "Ophthalmic Research": 2.0,
        "Journal of Glaucoma": 2.4,
        "Journal of Neuro-Ophthalmology": 2.2,
        "Cornea": 2.6,
        "International Journal of Ophthalmology": 1.6,
        "Journal of Ocular Pharmacology and Therapeutics": 1.9,
        "Seminars in Ophthalmology": 1.5,
        "Journal of Ophthalmology": 1.7,
        "BMC Ophthalmology": 1.8,
        "Ophthalmic Epidemiology": 1.9,
        "Current Eye Research": 2.0
    },
    "Dermatology": {
        "Journal of Dermatological Science": 3.8,
        "Dermatologic Therapy": 3.7,
        "Clinical and Experimental Dermatology": 3.7,
        "Experimental Dermatology": 3.5,
        "Acta Dermato-Venereologica": 3.5,
        "Dermatology and Therapy": 3.5,
        "International Journal of Dermatology": 3.5,
        "Burns": 3.2,
        "Indian Journal of Dermatology Venereology & Leprology": 3.2,
        "Journal of Cutaneous Medicine and Surgery": 3.1,
        "Annales de Dermatologie et de Venereologie": 3.1,
        "Dermatology": 3.0,
        "Journal of Dermatology": 2.9,
        "Journal of Dermatological Treatment": 2.9,
        "Skin Pharmacology and Physiology": 2.8,
        "International Journal of Cosmetic Science": 2.7,
        "International Wound Journal": 2.6,
        "Anais Brasileiros de Dermatologia": 2.6,
        "Dermatologic Surgery": 2.5,
        "Dermatology Practical & Conceptual": 2.5,
        "Photodermatology Photoimmunology & Photomedicine": 2.5,
        "Journal of Tissue Viability": 2.4,
        "Journal of Cosmetic Dermatology": 2.3,
        "Clinics in Dermatology": 2.3,
        "Dermatologica Sinica": 2.3,
        "Lasers in Surgery and Medicine": 2.2,
        "Australasian Journal of Dermatology": 2.2,
        "Dermatologica Clinica": 2.2,
        "European Journal of Dermatology": 2.0,
        "Skin Research and Technology": 2.0,
        "Veterinary Dermatology": 1.9,
        "Clinical Cosmetic and Investigational Dermatology": 1.9,
        "Archives of Dermatological Research": 1.8,
        "Advances in Skin & Wound Care": 1.7,
        "Journal of Cutaneous Pathology": 1.6,
        "International Journal of Lower Extremity Wounds": 1.5,
        "Annals of Dermatology": 1.5,
        "Melanoma Research": 1.5,
        "Journal of Wound Care": 1.5,
        "Journal of Burn Care & Research": 1.5,
        "Postepy Dermatologii (Alergologii)": 1.4,
        "Journal of Cosmetic and Laser Therapy": 1.2,
        "Journal of Investigative Dermatology": 8.6,  # High-impact journal
        "JAMA Dermatology": 9.3,  # High-impact journal
        "British Journal of Dermatology": 9.0  # High-impact journal
    }
    # More specialties will be added as needed
}

# Generic journal name patterns with estimated impact factors
# These are used for specialties without hard-coded data
GENERIC_PATTERNS = {
    r'^(new england journal of medicine|nejm)$': 91.2,
    r'^(lancet|the lancet)$': 79.3,
    r'^(journal of the american medical association|jama)$': 56.3,
    r'^(nature medicine)$': 53.4,
    r'^(bmj|british medical journal)$': 39.9,
    r'^(nature reviews \w+)$': 30.0,
    r'^(annual review of \w+)$': 20.0,
    r'^(cell \w+)$': 15.0,
    r'^(advances in \w+)$': 10.0,
    r'^(journal of \w+ and \w+)$': 8.5,
    r'^(international journal of \w+)$': 7.0,
    r'^(journal of \w+)$': 6.0,
    r'^(european journal of \w+)$': 5.5,
    r'^(american journal of \w+)$': 5.0,
    r'^(british journal of \w+)$': 4.5,
    r'^(current \w+)$': 4.0,
    r'^(\w+ journal)$': 3.5,
    r'^(\w+ research)$': 3.0,
    r'^(\w+ reviews)$': 2.5,
    r'^(\w+ practice)$': 2.0,
    r'^(\w+ proceedings)$': 1.5,
    r'^(\w+ communications)$': 1.0,
}

# List of known high-impact factor journals regardless of field
HIGH_IMPACT_JOURNALS = {
    "Science": 47.7,
    "Nature": 49.9,
    "Cell": 38.6,
    "PNAS": 11.2,
    "PLoS Medicine": 10.5,
    "JAMA Internal Medicine": 18.7,
    "BMJ": 39.9,
    "NEJM": 91.2,
    "Nature Medicine": 53.4,
    "Lancet": 79.3
}

def get_impact_factor(specialty: str, journal_name: str, default: float = 1.0) -> float:
    """Get the impact factor for a specific journal in a specialty.
    
    Args:
        specialty: The medical specialty (e.g., 'Allergy', 'Ophthalmology')
        journal_name: The name of the journal
        default: Default value to return if journal is not found
        
    Returns:
        The impact factor as a float
    """
    if not journal_name:
        return default
    
    # Clean the journal name
    journal_name_cleaned = journal_name.strip()
    journal_name_lower = journal_name_cleaned.lower()
    
    # First, check high-impact general journals
    for known_journal, impact in HIGH_IMPACT_JOURNALS.items():
        if known_journal.lower() == journal_name_lower or known_journal.lower() in journal_name_lower:
            return impact
    
    # Get the specialty dictionary, defaulting to empty dict if not found
    specialty_dict = JOURNAL_IMPACT_FACTORS.get(specialty, {})
    
    # First, try exact match
    if journal_name_cleaned in specialty_dict:
        return specialty_dict[journal_name_cleaned]
        
    # If not found, try case-insensitive match
    for key, value in specialty_dict.items():
        if key.lower() == journal_name_lower:
            return value
            
    # Try partial match (journal name contains key or key contains journal name)
    for key, value in specialty_dict.items():
        if journal_name_lower in key.lower() or key.lower() in journal_name_lower:
            # Make sure it's a significant match (at least 70% of the shorter string)
            shorter = min(len(journal_name_lower), len(key.lower()))
            if (shorter > 5) and (max(journal_name_lower.count(key.lower()), 
                                    key.lower().count(journal_name_lower)) / shorter > 0.7):
                return value
    
    # If we get here, try to match against generic patterns
    for pattern, impact in GENERIC_PATTERNS.items():
        if re.search(pattern, journal_name_lower):
            # Adjust based on whether the specialty name is in the journal name
            if specialty.lower() in journal_name_lower:
                # Journals specifically focused on a specialty often have higher impact
                return impact * 1.2  # 20% increase
            return impact
    
    # Estimate based on parts of the name
    estimated_impact = estimate_impact_from_name(journal_name_lower, specialty.lower())
    if estimated_impact > 0:
        return estimated_impact
    
    # If we get here, no match was found
    return default

def estimate_impact_from_name(journal_name: str, specialty: str) -> float:
    """Estimate impact factor based on journal name characteristics."""
    base_impact = 1.0
    
    # Prestigious publishers/societies typically have higher impact factors
    prestigious_indicators = [
        "nature", "cell", "lancet", "jama", "nejm", "bmj", "science", 
        "elsevier", "wiley", "oxford", "cambridge", "american", "european",
        "international", "world", "royal", "society"
    ]
    
    # Types of publications with generally higher impact
    higher_impact_types = [
        "review", "advances", "trends", "progress", "annual", "current"
    ]
    
    # Adjust impact based on prestige indicators
    for indicator in prestigious_indicators:
        if indicator in journal_name:
            base_impact *= 1.5
            break
    
    # Adjust impact based on publication type
    for pub_type in higher_impact_types:
        if pub_type in journal_name:
            base_impact *= 1.3
            break
    
    # Adjust for having the specialty name in the journal
    if specialty in journal_name:
        base_impact *= 1.2
    
    # Cap the estimated impact within reasonable bounds
    if base_impact > 15.0:
        base_impact = 15.0
    
    return round(base_impact, 1)

def get_all_specialties() -> List[str]:
    """Get a list of all supported medical specialties.
    
    This includes specialties with hardcoded data and the complete list
    of specialties that can be queried from OOIR.org.
    """
    # All possible medical specialties from OOIR.org
    all_specialties = [
        "Allergy", "Andrology", "Anesthesiology", "Audiology & Speech-Language Pathology",
        "Behavioral Sciences", "Cardiac & Cardiovascular Systems", "Clinical Neurology",
        "Critical Care Medicine", "Dentistry, Oral Surgery & Medicine", "Dermatology",
        "Emergency Medicine", "Endocrinology & Metabolism", "Engineering, Biomedical",
        "Gastroenterology & Hepatology", "Genetics & Heredity", "Geriatrics & Gerontology",
        "Health Care Sciences & Services", "Health Policy & Services", "Hematology",
        "Immunology", "Infectious Diseases", "Integrative & Complementary Medicine",
        "Materials Science, Biomaterials", "Medical Ethics", "Medical Informatics",
        "Medical Laboratory Technology", "Medicine, General & Internal", "Medicine, Legal",
        "Medicine, Research & Experimental", "Neuroimaging", "Neurosciences", "Nursing",
        "Nutrition & Dietetics", "Obstetrics & Gynecology", "Oncology", "Ophthalmology",
        "Orthopedics", "Otorhinolaryngology", "Pathology", "Pediatrics",
        "Peripheral Vascular Disease", "Pharmacology & Pharmacy", "Primary Health Care",
        "Psychiatry", "Psychology, Clinical", "Public, Environmental & Occupational Health",
        "Radiology, Nuclear Medicine & Medical Imaging", "Rehabilitation", "Reproductive Biology",
        "Respiratory System", "Rheumatology", "Sport Sciences", "Substance Abuse", "Surgery",
        "Toxicology", "Transplantation", "Tropical Medicine", "Urology & Nephrology", "Virology"
    ]
    
    return all_specialties 