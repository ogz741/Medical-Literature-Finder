// Main JavaScript file for the frontend application.
// This will be populated with logic for tabs, API calls, DOM manipulation, etc.

console.log("main.js loaded.");

// Global variables 
let currentTab = '';
let rankingsData = {}; // Store ranking data
let availableDates = []; // Store available dates for journal rankings
let lastSelectedSpecialty = null; // To store the last selected specialty from the Rankings tab

// UPDATED: Default MeSH Terms
const DEFAULT_MESH_TERMS = [
    "Education, Medical",
    "Education, Medical, Graduate",
    "Education, Medical, Undergraduate",
    "Education, Medical, Continuing",
    "Internship and Residency",
    "Clinical Competence",
    "Curriculum",
    "Competency-Based Education",
    "Teaching",
    "Medical Education", 
    "Educational Measurement",
    "Schools, Medical",
    "Simulation Training",
    "Patient Simulation",
    "Problem-Based Learning",
    "Teaching Materials",
    "Faculty, Medical",
    "Mentors",
    "Educational Technology",
    "Program Development",
    "Program Evaluation",
    "Certification",
    "Fellowships and Scholarships",
    "Attitude of Health Personnel",
    "Specialty Boards"
];

// Global variable to store the current search query and filters for download
let currentSearchParamsForDownload = {
    query: '',
    journals: [],
    // MeSH terms will be fetched by backend if not explicitly sent
    // filter_date_start: null, // Optional: Add if UI supports date ranges for search
    // filter_date_end: null,   // Optional: Add if UI supports date ranges for search
};

// Add a simple in-memory cache to reduce API calls
const meshTreeCache = {
    data: {},
    set: function(key, value, ttlMinutes = 30) {
        const now = new Date();
        const expiry = new Date(now.getTime() + ttlMinutes * 60000);
        this.data[key] = {
            value: value,
            expiry: expiry
        };
        // console.log(`Cache: Stored ${key}. Expires in ${ttlMinutes} minutes.`);
    },
    get: function(key) {
        if (!this.data[key]) return null;
        const now = new Date();
        if (now > this.data[key].expiry) {
            delete this.data[key];
            return null;
        }
        return this.data[key].value;
    },
    clear: function() {
        this.data = {};
        // console.log("Cache: Cleared all entries.");
    }
};

// Store selected journals for search
const selectedJournals = {
    items: [],
    add: function(journal) {
        if (!this.items.some(item => item.journal_name === journal.journal_name)) {
            this.items.push(journal);
            return true;
        }
        return false;
    },
    remove: function(journalName) {
        const initialLength = this.items.length;
        this.items = this.items.filter(item => item.journal_name !== journalName);
        return this.items.length < initialLength;
    },
    getAll: function() {
        return this.items;
    },
    clear: function() {
        this.items = [];
    }
};

// Moved showMessage to a broader scope to be accessible by all functions
function showMessage(type, text, duration = 3000) {
    const statusMessages = document.getElementById('status-messages'); 
    if (!statusMessages) {
        console.error("'status-messages' element not found for showMessage");
        return;
    }
    statusMessages.innerHTML = `<div class="${type}">${text}</div>`;
    if (duration > 0) {
        setTimeout(() => { 
            if(statusMessages) statusMessages.innerHTML = ''; 
        }, duration);
    }
}

// Function to show a notification (ensure this is styled in CSS)
function showNotification(message, duration = 3000) {
    const notificationArea = document.getElementById('notification-area'); 
    if (!notificationArea) {
        console.warn("Notification area not found. One will be created.");
        const newArea = document.createElement('div');
        newArea.id = 'notification-area';
        newArea.style.position = 'fixed';
        newArea.style.top = '20px';
        newArea.style.right = '20px';
        newArea.style.zIndex = '10000'; 
        document.body.appendChild(newArea);
        // Call again to use the newly created area
        return showNotification(message, duration);
    }

    const notification = document.createElement('div');
    notification.className = 'notification'; 
    notification.textContent = message;
    
    notificationArea.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('show'); 
    }, 10); 
    
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            if (notification.parentNode) { 
                 notification.remove();
            }
        }, 500); 
    }, duration);
}

// NEW FUNCTION: Show notification with an Undo button
function showNotificationWithUndo(message, onUndoCallback, duration = 7000) {
    const notificationArea = document.getElementById('notification-area');
    if (!notificationArea) {
        // Attempt to create notification area if it doesn't exist
        console.warn("Notification area not found for Undo. One will be created.");
        const newArea = document.createElement('div');
        newArea.id = 'notification-area';
        newArea.style.position = 'fixed';
        newArea.style.top = '20px';
        newArea.style.right = '20px';
        newArea.style.zIndex = '10000';
        document.body.appendChild(newArea);
        return showNotificationWithUndo(message, onUndoCallback, duration); // Retry with created area
    }

    const notification = document.createElement('div');
    notification.className = 'notification undo-notification'; // For potential custom styling

    const messageSpan = document.createElement('span');
    messageSpan.textContent = message + ' ';
    messageSpan.style.marginRight = '10px';
    notification.appendChild(messageSpan);

    const undoButton = document.createElement('button');
    undoButton.textContent = 'Undo';
    undoButton.className = 'btn-undo';
    Object.assign(undoButton.style, {
        background: 'none',
        border: 'none',
        color: '#007bff', // Link-like color
        textDecoration: 'underline',
        cursor: 'pointer',
        padding: '0',
        fontSize: 'inherit' // Inherit font size from notification
    });

    let timeoutId = null;

    const removeNotification = (isUndo = false) => {
        if (timeoutId) {
            clearTimeout(timeoutId);
            timeoutId = null;
        }
        // Start fade out animation
        notification.classList.remove('show'); 
        // Remove from DOM after animation
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 500); // This duration should match any CSS fade-out transition
        
        if (isUndo) {
            onUndoCallback(); // Call the provided undo logic
        }
    };

    undoButton.onclick = () => {
        removeNotification(true); // Pass true to indicate it's an undo action
    };
    notification.appendChild(undoButton);

    notificationArea.appendChild(notification);

    // Add 'show' class to trigger fade-in animation (if any)
    setTimeout(() => {
        notification.classList.add('show');
    }, 10); // Small delay to ensure element is in DOM for transition

    // Set timeout to automatically remove the notification if not undone
    timeoutId = setTimeout(() => removeNotification(false), duration);
}

// --- Journal Rankings Tab --- 
async function renderJournalRankingsTab() {
    const contentPlaceholder = document.getElementById('content-placeholder');
    if (!contentPlaceholder) { console.error("renderJournalRankingsTab: contentPlaceholder not found"); return; }
    contentPlaceholder.innerHTML = ''; 

    const heading = document.createElement('h2');
    heading.textContent = 'Journal Rankings';
    contentPlaceholder.appendChild(heading);

    const controlsContainer = document.createElement('div');
    controlsContainer.className = 'controls-container';
    Object.assign(controlsContainer.style, { display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap' });

    const specialtySelect = document.createElement('select');
    specialtySelect.id = 'specialty-select';
    Object.assign(specialtySelect.style, { flexGrow: '1', minWidth: '200px', padding: '8px', borderRadius: '4px', border: '1px solid #d1d5db' });
    specialtySelect.innerHTML = '<option disabled selected>Loading specialties...</option>';

    const refreshButton = document.createElement('button');
    refreshButton.textContent = 'Refresh Data';
    refreshButton.id = 'refresh-rankings-btn';
    refreshButton.className = 'secondary-btn';

    controlsContainer.appendChild(specialtySelect);
    controlsContainer.appendChild(refreshButton);
    contentPlaceholder.appendChild(controlsContainer);
    
    const rankingsDisplay = document.createElement('div');
    rankingsDisplay.id = 'rankings-display';
    rankingsDisplay.innerHTML = '<div class="loading">Loading...</div>';
    contentPlaceholder.appendChild(rankingsDisplay);

    try {
        const response = await fetch('/api/available-specialties');
        const data = await response.json();

        if (data.status === 'success' && Array.isArray(data.specialties)) {
            specialtySelect.innerHTML = ''; // Clear loading
            data.specialties.forEach(specialty => {
                const option = document.createElement('option');
                option.value = specialty;
                option.textContent = specialty;
                specialtySelect.appendChild(option);
            });

            // Updated default specialty logic from previous step
            const defaultSpecialtyValue = data.specialties.includes('Ophthalmology') ? 'Ophthalmology' : (data.specialties.includes('Dermatology') ? 'Dermatology' : (data.specialties[0] || null));
            if (defaultSpecialtyValue) {
                specialtySelect.value = defaultSpecialtyValue;
                lastSelectedSpecialty = defaultSpecialtyValue; // Initialize lastSelectedSpecialty
            }

            specialtySelect.addEventListener('change', () => {
                lastSelectedSpecialty = specialtySelect.value; // Update on change
                fetchAndDisplayRankings(specialtySelect.value);
            });
            refreshButton.addEventListener('click', async () => {
                rankingsDisplay.innerHTML = '<div class="loading">Refreshing journal rankings...</div>';
                lastSelectedSpecialty = specialtySelect.value; // Ensure it's current before refresh potentially triggers other actions
                try {
                    const liveDataUrl = `/api/journal-rankings/${encodeURIComponent(specialtySelect.value)}?refresh=true`;
                    const liveResponse = await fetch(liveDataUrl);
                    const liveData = await liveResponse.json();
                    if (liveData.status === 'success') {
                        rankingsData = liveData.data;
                        displayRankings(rankingsData);
                        showNotification('Journal rankings refreshed successfully');
                    } else {
                        rankingsDisplay.innerHTML = `<div class="error">Error: ${liveData.message || 'Failed to refresh rankings'}</div>`;
                    }
                } catch (err) {
                    console.error('Error refreshing rankings:', err);
                    rankingsDisplay.innerHTML = '<div class="error">Error refreshing. Please try again.</div>';
                }
            });

            if (lastSelectedSpecialty) await fetchAndDisplayRankings(lastSelectedSpecialty);
            else if (data.specialties.length > 0) { 
                 specialtySelect.value = data.specialties[0];
                 lastSelectedSpecialty = data.specialties[0];
                 await fetchAndDisplayRankings(data.specialties[0]);
            } else {
                 rankingsDisplay.innerHTML = '<div class="info">No specialties available to display rankings.</div>';
            }
        } else {
            specialtySelect.innerHTML = '<option>Error loading</option>';
            rankingsDisplay.innerHTML = `<div class="error">Error fetching specialties: ${data.message || 'Unknown error'}</div>`;
        }
    } catch (error) {
        console.error('Error fetching specialties:', error);
        specialtySelect.innerHTML = '<option>Error loading</option>';
        rankingsDisplay.innerHTML = '<div class="error">Could not fetch specialties. Please try again later.</div>';
    }
}

async function fetchAndDisplayRankings(specialty) {
    const display = document.getElementById('rankings-display');
    if (!display) { console.error("fetchAndDisplayRankings: rankings-display not found"); return; }
    display.innerHTML = '<div class="loading">Loading journal rankings...</div>';
    try {
        const url = `/api/journal-rankings/${encodeURIComponent(specialty)}`;
        const response = await fetch(url);
        const data = await response.json();
        if (data.status === 'success') {
            rankingsData = data.data;
            displayRankings(rankingsData);
        } else {
            display.innerHTML = `<div class="error">Error: ${data.message || 'Failed to fetch rankings'}</div>`;
        }
    } catch (error) {
        console.error('Error fetching rankings:', error);
        display.innerHTML = '<div class="error">Error fetching rankings. Please try again.</div>';
    }
}

function displayRankings(rankings) {
    const display = document.getElementById('rankings-display');
    if (!display) { console.error("displayRankings: rankings-display not found"); return; }
    const noteHtml = `
        <div class="info-box" style="padding: 10px; margin-bottom: 15px; border: 1px solid #eee; border-radius: 4px; background-color: #f9f9f9;">
            <h4 style="margin-top: 0; margin-bottom: 10px; color: #2563eb;">About Journal Impact Factors</h4>
            <p style="font-size: 0.9em; margin-bottom: 5px;">The values shown are Journal Impact Factors (JIF).</p>
            <p style="font-size: 0.9em; margin-bottom: 0;">JIF represents the average citations per paper in that journal over the two preceding years.</p>
        </div>`;

    if (!rankings || rankings.length === 0) {
        display.innerHTML = noteHtml + '<p>No journal rankings available for this specialty.</p>';
        return;
    }
    let tableHTML = `
        <table class="rankings-table">
            <thead><tr><th>Rank</th><th>Journal</th><th>Impact Factor</th><th>Actions</th></tr></thead>
            <tbody>`;
    rankings.forEach((journal, index) => {
        const impactFactorFormatted = parseFloat(journal.impact_factor).toFixed(1);
        const isAlreadySelected = selectedJournals.getAll().some(item => item.journal_name === journal.journal_name);
        tableHTML += `
            <tr>
                <td>${index + 1}</td>
                <td>${journal.journal_name}</td>
                <td>${impactFactorFormatted}</td>
                <td>
                    <button class="add-to-search-btn ${isAlreadySelected ? 'btn-added' : ''}" 
                            data-journal='${JSON.stringify(journal)}' 
                            ${isAlreadySelected ? 'disabled' : ''}>
                        ${isAlreadySelected ? 'Added' : 'Add to Search'}
                    </button>
                </td>
            </tr>`;
    });
    tableHTML += `</tbody></table>`;
    display.innerHTML = noteHtml + tableHTML;

    document.querySelectorAll('.add-to-search-btn').forEach(button => {
        button.addEventListener('click', function() {
            if (this.disabled) return;
            const journalData = JSON.parse(this.getAttribute('data-journal'));
            if (selectedJournals.add(journalData)) {
                showNotification(`Added "${journalData.journal_name}" to search criteria`);
                updateSelectedJournalsDisplay();
                this.textContent = 'Added';
                this.classList.add('btn-added');
                this.disabled = true;
            }
        });
    });
}

// --- Selected Journals Display & Management --- 
function updateSelectedJournalsDisplay() {
    const selectedJournalsList = document.getElementById('selected-journals-list');
    if (!selectedJournalsList) return; // If the element isn't on the current tab
    const journals = selectedJournals.getAll();
    if (journals.length === 0) {
        selectedJournalsList.innerHTML = '<p>No journals selected. Use the Journal Rankings tab to add journals.</p>';
        return;
    }
    let html = '<ul class="selected-journals">';
    journals.forEach(journal => {
        html += `
            <li>
                <span class="journal-name">${journal.journal_name}</span>
                <span class="journal-if">(IF: ${parseFloat(journal.impact_factor).toFixed(1)})</span>
                <button class="remove-journal-btn" data-journal-name="${journal.journal_name}"><i class="fa fa-times"></i> Remove</button>
            </li>`;
    });
    html += '</ul>';
    selectedJournalsList.innerHTML = html;
    document.querySelectorAll('.remove-journal-btn').forEach(button => button.addEventListener('click', handleRemoveJournal));
}

function handleRemoveJournal(event) {
    const journalName = event.currentTarget.dataset.journalName;
    if (selectedJournals.remove(journalName)) {
        showNotification(`Removed "${journalName}" from search criteria`);
        updateSelectedJournalsDisplay();
        // Reflect change in rankings tab if visible
        document.querySelectorAll('#rankings-display .add-to-search-btn').forEach(btn => {
            try {
                const btnJournalData = JSON.parse(btn.dataset.journal);
                if (btnJournalData.journal_name === journalName) {
                    btn.textContent = 'Add to Search';
                    btn.classList.remove('btn-added');
                    btn.disabled = false;
                }
            } catch(e) { console.warn("Error parsing journal data for button update:", e); }
        });
    }
}

// --- Article Search Tab & Helpers --- 
async function handleArticleSearch() {
    const searchInput = document.getElementById('pubmed-search-input');
    const resultsContainer = document.getElementById('search-results');
    const downloadButton = document.getElementById('downloadResultsButton');
    const queryText = searchInput ? searchInput.value.trim() : '';

    currentSearchParamsForDownload.query = queryText;
    const currentSelectedJournals = selectedJournals.getAll();
    let journalsForApiCall = currentSelectedJournals.map(j => j.journal_name);
    const userMeshTerms = await fetchUserMeshTerms(); 

    if (!queryText && userMeshTerms.length === 0) {
        showNotification('Please enter a search query, or add MeSH terms (via the MeSH tab) to enable MeSH-based search.', 4000);
        if(resultsContainer) resultsContainer.innerHTML = '<p>Please provide a search query or ensure you have MeSH terms saved in your profile to proceed.</p>';
        if(downloadButton) downloadButton.disabled = true;
        return;
    }

    if (currentSelectedJournals.length === 0) { // No specific journals hand-picked
        if (lastSelectedSpecialty) {
            const proceedWithSpecialty = window.confirm(`You have not selected any specific journals. This search will query all journals under the '${lastSelectedSpecialty}' specialty. Do you want to proceed?`);
            if (!proceedWithSpecialty) {
                if(resultsContainer) resultsContainer.innerHTML = '<p>Search cancelled. Select specific journals or confirm specialty search.</p>';
                return; // Abort search
            }
            // User confirmed search by specialty. Fetch journals for this specialty.
            if(resultsContainer) resultsContainer.innerHTML = `<div class="loading">Fetching journals for ${lastSelectedSpecialty}...</div>`;
            try {
                const rankingsResponse = await fetch(`/api/rankings/${encodeURIComponent(lastSelectedSpecialty)}`);
                if (!rankingsResponse.ok) {
                    const errorData = await rankingsResponse.json().catch(() => ({detail: `Failed to fetch journals for ${lastSelectedSpecialty}.`}));
                    throw new Error(errorData.detail || `HTTP error ${rankingsResponse.status}`);
                }
                const specialtyJournalsData = await rankingsResponse.json(); // Expects array of journal objects [{journal_name: "..."}, ...]
                
                if (specialtyJournalsData && specialtyJournalsData.length > 0) {
                    journalsForApiCall = specialtyJournalsData.map(j => j.journal_name);
                    if (journalsForApiCall.length === 0) { // Should be caught by specialtyJournalsData.length > 0, but defensive
                        showNotification(`No journal names found under the '${lastSelectedSpecialty}' specialty. Will try to search all of PubMed.`, 'warning', 5000);
                        const proceedAllPubMed = window.confirm(`No journals could be specifically identified for '${lastSelectedSpecialty}'. Do you want to search all of PubMed instead?`);
                        if (!proceedAllPubMed) { if(resultsContainer) resultsContainer.innerHTML = '<p>Search cancelled.</p>'; return; }
                        journalsForApiCall = []; // Explicitly empty for all PubMed search
                    } else {
                        showNotification(`Searching within ${journalsForApiCall.length} journals for the '${lastSelectedSpecialty}' specialty.`, 'info', 4000);
                    }
                } else {
                    showNotification(`No journals found listed under the '${lastSelectedSpecialty}' specialty. Will try to search all of PubMed.`, 'warning', 5000);
                    const proceedAllPubMed = window.confirm(`No journals could be found for the specialty '${lastSelectedSpecialty}'. Do you want to search all of PubMed instead?`);
                    if (!proceedAllPubMed) { if(resultsContainer) resultsContainer.innerHTML = '<p>Search cancelled.</p>'; return; }
                    journalsForApiCall = []; // Explicitly empty for all PubMed search
                }
            } catch (error) {
                console.error('Error fetching journals for specialty:', error);
                showNotification(`Error fetching journals for '${lastSelectedSpecialty}': ${error.message}. Will try to search all of PubMed.`, 'error', 5000);
                const proceedAllPubMedOnError = window.confirm(`Could not fetch journal list for '${lastSelectedSpecialty}'. Do you want to search all of PubMed instead?`);
                if (!proceedAllPubMedOnError) { if(resultsContainer) resultsContainer.innerHTML = '<p>Search cancelled.</p>'; return; }
                journalsForApiCall = []; // Explicitly empty for all PubMed search
            }
        } else { // No lastSelectedSpecialty, fall back to all PubMed confirmation
            const proceedAllPubMed = window.confirm("You have not selected any specific journals, and no default specialty is active. This search will query all journals in PubMed. Do you want to proceed?");
            if (!proceedAllPubMed) {
                if(resultsContainer) resultsContainer.innerHTML = '<p>Search cancelled by user. Select specific journals or confirm to search all of PubMed.</p>';
                return; // Abort search
            }
            journalsForApiCall = []; // Explicitly empty for all PubMed search
        }
    }

    currentSearchParamsForDownload.journals = journalsForApiCall; // Update global download params

    if (!queryText && userMeshTerms.length > 0 && journalsForApiCall.length === 0) {
      showNotification(`No search query entered. Searching using your ${userMeshTerms.length} saved MeSH term(s) across all of PubMed.`, 3500);
    } else if (!queryText && userMeshTerms.length > 0 && journalsForApiCall.length > 0) {
      showNotification(`No search query entered. Searching using your ${userMeshTerms.length} saved MeSH term(s) within selected/specialty journals.`, 3500);
    }

    if(resultsContainer) resultsContainer.innerHTML = '<div class="loading">Searching articles...</div>';
    if(downloadButton) downloadButton.disabled = true;

    try {
        const params = new URLSearchParams({ page: '1', per_page: '10' }); 
        if (queryText) { 
            params.append('query', queryText);
        }
        
        if (journalsForApiCall.length > 0) { // Only add journal filter if we have specific journals
            params.append('journals', journalsForApiCall.join(','));
        }
        
        const response = await fetch(`/api/search-pubmed?${params.toString()}`);
        const data = await response.json();
        if (data.status === 'success') {
            displaySearchResults(data.results);
        } else {
            if(resultsContainer) resultsContainer.innerHTML = `<div class="error">Error: ${data.message || 'Failed to search articles'}</div>`;
            if(downloadButton) downloadButton.disabled = true;
        }
    } catch (error) {
        console.error('Error searching articles:', error);
        if(resultsContainer) resultsContainer.innerHTML = '<div class="error">Error searching articles. Please try again later.</div>';
        if(downloadButton) downloadButton.disabled = true;
    }
}

async function fetchUserMeshTerms() {
    try {
        const response = await fetch('/api/mesh-terms');
        if (!response.ok) return [];
        const termsData = await response.json(); // Expecting list of {id: string, term: string}
        return termsData.map(t => t.term); // Extract just the term strings
    } catch (e) {
        console.error("Failed to fetch user MeSH terms for validation:", e);
        return [];
    }
}

let currentDisplayedArticles = []; // Store articles from the current view for potential direct use

async function handleBookmarkArticleClick(button) {
    const articleDataString = button.dataset.article;
    if (!articleDataString) {
        showMessage('error', 'Article data not found for bookmarking.');
        return;
    }
    let articleData;
    try { articleData = JSON.parse(articleDataString); } 
    catch (e) { showMessage('error', 'Invalid article data for bookmarking.'); console.error("Error parsing article data for bookmark:", e); return; }

    // Prepare payload for the backend
    const payload = {
        pmid: articleData.pubmed_id || articleData.pmid, 
        title: articleData.title,
        authors: Array.isArray(articleData.authors) ? articleData.authors.join(', ') : (articleData.authors || ''),
        journal: articleData.journal,
        pub_date: articleData.publication_date || articleData.pub_date, 
        abstract: articleData.abstract
    };
    if (!payload.pmid) { showMessage('error', 'Article PMID is missing, cannot bookmark.'); return; }

    showMessage('loading', `Bookmarking "${payload.title}"...`, 0);
    try {
        const response = await fetch('/api/bookmark-article', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Failed to bookmark.' }));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        await response.json(); 
        showMessage('success', `Bookmarked "${payload.title}"`);
        button.textContent = 'Bookmarked ✓';
        button.classList.add('btn-bookmarked'); 
        button.disabled = true;
    } catch (error) {
        console.error("Error bookmarking article:", error);
        showMessage('error', `Could not bookmark: ${error.message}`);
    }
}

async function handleCiteArticleClick(button) {
    const pmid = button.dataset.pmid;
    const title = button.dataset.title || "article"; 
    if (!pmid) { showMessage('error', 'PMID not found for citation.'); return; }

    showMessage('loading', `Preparing citation for "${title}" (PMID: ${pmid})...`, 0);
    try {
        const response = await fetch(`/api/cite-article/${pmid}`);
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: `Failed to get citation. Status: ${response.status}` }));
            throw new Error(errorData.detail || `HTTP error ${response.status}`);
        }
        const blob = await response.blob();
        const filenameHeader = response.headers.get('content-disposition');
        let filename = `cite_${pmid}.nbib`; 
        if (filenameHeader) {
            const filenameMatch = filenameHeader.match(/filename=([^;]+)/);
            if (filenameMatch && filenameMatch.length > 1) filename = filenameMatch[1].replace(/"/g, ''); // Remove quotes
        }
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(link.href);
        showMessage('success', `Citation for "${title}" downloaded as ${filename}.`);
        button.textContent = 'Cited ✓';
        button.classList.add('btn-cited'); 
        button.disabled = true;
    } catch (error) {
        console.error("Error fetching citation:", error);
        showMessage('error', `Could not fetch citation: ${error.message}`);
    }
}

function displaySearchResults(results) {
    const resultsContainer = document.getElementById('search-results');
    const downloadButton = document.getElementById('downloadResultsButton');
    if (!resultsContainer) { console.error("displaySearchResults: resultsContainer not found."); return; }
    currentDisplayedArticles = results.articles || [];

    if (!results || !results.articles || results.articles.length === 0) {
        resultsContainer.innerHTML = '<div class="no-results">No articles found matching your search criteria.</div>';
        if (downloadButton) downloadButton.disabled = true;
        return;
    }
    
    let html = `
        <div class="results-header">
            <h3>Found ${results.total} results</h3>
            <p>Showing page ${results.page} of ${Math.ceil(results.total / results.per_page)}</p>
        </div>
        <ul class="articles-list">`;
    
    results.articles.forEach(article => {
        const titleText = article.title || 'No title available';
        // Ensure authors are displayed as a string
        const authorsText = Array.isArray(article.authors) ? article.authors.join(', ') : (article.authors || 'Unknown authors');
        const journalText = article.journal || '';
        const pubDateText = article.publication_date || '';
        const abstractText = article.abstract || 'No abstract available';
        const pmid = article.pmid || article.pubmed_id; 

        // Prepare article data for bookmarking, ensuring it's a flat object for stringify
        const articleForBookmark = {
            pubmed_id: pmid,
            title: article.title, // original title
            authors: article.authors, // pass as array, stringify will handle
            journal: article.journal,
            publication_date: article.publication_date,
            abstract: article.abstract
        };
        
        html += `
            <li class="article-item">
                <h4 class="article-title">${titleText}</h4>
                <div class="article-meta">
                    <span class="article-authors">${authorsText}</span>
                    <span class="article-journal">${journalText}</span>
                    <span class="article-date">${pubDateText}</span>
                </div>
                <div class="article-abstract">
                    <p>${abstractText}</p>
                </div>
                <div class="article-actions">
                    ${ pmid ? `<a href="https://pubmed.ncbi.nlm.nih.gov/${pmid}" target="_blank" class="article-link">View on PubMed</a>` : ''}
                    <button class="bookmark-btn" data-article='${JSON.stringify(articleForBookmark)}'>Bookmark</button>
                    ${ pmid ? `<button class="cite-btn" data-pmid="${pmid}" data-title="${titleText.replace(/'/g, "\'")}">Cite</button>` : ''}
                </div>
            </li>`;
    });
    
    html += '</ul>';
    html += `
        <div class="pagination">
            <button id="prev-page" ${results.page <= 1 ? 'disabled' : ''}>Previous Page</button>
            <span>Page ${results.page}</span>
            <button id="next-page" ${results.page >= Math.ceil(results.total / results.per_page) ? 'disabled' : ''}>Next Page</button>
        </div>`;
    
    resultsContainer.innerHTML = html;
    
    document.querySelectorAll('.bookmark-btn').forEach(button => {
        button.addEventListener('click', function() { handleBookmarkArticleClick(this); });
    });

    document.querySelectorAll('.cite-btn').forEach(button => {
        button.addEventListener('click', function() { handleCiteArticleClick(this); });
    });
    
    // TODO: Implement pagination functionality

    if (downloadButton) downloadButton.disabled = false;
}

async function handleDownloadResults() {
    const formatSelect = document.getElementById('download-format-select');
    if (!formatSelect) { showMessage('error', 'Download format selector not found.'); return; }
    const selectedFormat = formatSelect.value;

    const payload = {
        query: currentSearchParamsForDownload.query,
        journals: currentSearchParamsForDownload.journals,
        // MeSH terms will be automatically added by the backend if user has them saved
        format: selectedFormat,
        max_results: 500 // Default, consider making configurable
    };

    showMessage('loading', `Preparing ${selectedFormat.toUpperCase()} download... Please wait.`, 0);

    try {
        const response = await fetch('/api/download-search-results', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: `Failed to start download. Status: ${response.status}` }));
            throw new Error(errorData.detail || `HTTP error ${response.status}`);
        }

        const blob = await response.blob();
        const filenameHeader = response.headers.get('content-disposition');
        let filename = `search-results.${selectedFormat}`;
        if (filenameHeader) {
            const filenameMatch = filenameHeader.match(/filename=([^;]+)/);
            if (filenameMatch && filenameMatch.length > 1) filename = filenameMatch[1].replace(/"/g, ''); 
        }

        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(link.href);
        showMessage('success', `Results downloaded as ${filename}`);

    } catch (error) {
        console.error("Error downloading results:", error);
        showMessage('error', `Download failed: ${error.message}`);
    }
}

function renderSearchArticlesTab() {
    const contentPlaceholder = document.getElementById('content-placeholder');
    if (!contentPlaceholder) { console.error("renderSearchArticlesTab: contentPlaceholder not found"); return; }
    contentPlaceholder.innerHTML = `
        <h2>Search Articles</h2>
        
        <div id="selected-journals-container">
            <h3>Journals Selected for Current Search:</h3>
            <div id="selected-journals-list"><p>No journals selected. Use the Journal Rankings tab to add journals.</p></div>
        </div>

        <div class="search-controls">
            <input type="text" id="pubmed-search-input" placeholder="Enter search query (e.g., glaucoma treatment)">
        </div>
        <div class="search-actions">
            <button id="searchArticlesButton">Search Articles</button>
            <div class="download-controls" style="display: inline-block; margin-left: 10px;">
                <select id="download-format-select" style="padding: 8px; border-radius: 4px; vertical-align: middle;">
                    <option value="csv">CSV</option>
                    <option value="xlsx">Excel (XLSX)</option>
                    <option value="json">JSON</option>
                    <option value="bibtex">BibTeX (.bib)</option>
                </select>
                <button id="downloadResultsButton" disabled style="vertical-align: middle; margin-left: 5px;">Download Results</button> 
            </div>
        </div>
        
        <div id="search-results" class="results-container">
            <!-- Results will be displayed here -->
        </div>`;

    updateSelectedJournalsDisplay(); 

    const searchBtn = document.getElementById('searchArticlesButton');
    const downloadBtn = document.getElementById('downloadResultsButton');
    if (searchBtn) searchBtn.addEventListener('click', handleArticleSearch);
    if (downloadBtn) downloadBtn.addEventListener('click', handleDownloadResults);
}

// --- Bookmarks Tab Logic --- 
async function renderBookmarksTab() {
    const contentPlaceholder = document.getElementById('content-placeholder');
    if (!contentPlaceholder) { console.error("renderBookmarksTab: contentPlaceholder not found"); return; }
    contentPlaceholder.innerHTML = `
        <h2>Bookmarked Articles</h2>
        <div id="bookmarked-articles-list" class="results-container">
            <div class="loading">Loading bookmarks...</div>
        </div>`;
    await loadBookmarkedArticles();
}

async function loadBookmarkedArticles() {
    const bookmarksListDiv = document.getElementById('bookmarked-articles-list');
    if (!bookmarksListDiv) { console.error("loadBookmarkedArticles: bookmarked-articles-list not found"); return; }
    bookmarksListDiv.innerHTML = '<div class="loading">Loading bookmarks...</div>';
    try {
        const response = await fetch('/api/bookmarked-articles');
        if (!response.ok) {
            const errorData = await response.json().catch(()=> ({detail: "Failed to fetch bookmarks"}));
            throw new Error(errorData.detail || 'Failed to fetch bookmarks');
        }
        const responseData = await response.json(); 
        // Ensure the backend response structure is handled: {status: "success", bookmarks: []}
        const bookmarks = responseData.bookmarks; 

        if (!bookmarks || bookmarks.length === 0) {
            bookmarksListDiv.innerHTML = '<p>No articles bookmarked yet.</p>';
            return;
        }
        let html = '<ul class="articles-list">';
        bookmarks.forEach(article => {
            const title = article.title || 'No title available';
            const authors = article.authors || 'Unknown authors'; // DB stores as string
            const journal = article.journal || '';
            const pubDate = article.pub_date || ''; 
            const abstract = article.abstract || 'No abstract available';
            const pmid = article.pmid || article.pubmed_id || 'N/A'; 

            html += `
                <li class="article-item">
                    <h4 class="article-title">${title}</h4>
                    <div class="article-meta">
                        <span class="article-authors">${authors}</span>
                        <span class="article-journal">${journal}</span>
                        <span class="article-pubdate">${pubDate}</span>
                    </div>
                    <p class="article-abstract">${abstract}</p>
                    <div class="article-actions">
                        ${pmid !== 'N/A' ? `<a href="https://pubmed.ncbi.nlm.nih.gov/${pmid}/" target="_blank" class="action-link">View on PubMed</a>` : ''}
                        <button class="remove-bookmark-btn" data-pmid="${pmid}">Remove Bookmark</button>
                    </div>
                </li>`;
        });
        html += '</ul>';
        bookmarksListDiv.innerHTML = html;

        document.querySelectorAll('.remove-bookmark-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const pmidToRemove = event.target.dataset.pmid;
                if (!pmidToRemove || pmidToRemove === 'N/A') {
                    showMessage('error', 'Invalid PMID for bookmark removal.');
                    return;
                }
                showMessage('loading', 'Removing bookmark...', 0);
                try {
                    const deleteResponse = await fetch(`/api/bookmark-article/${pmidToRemove}`, { method: 'DELETE' });
                    if (!deleteResponse.ok) {
                        const errorData = await deleteResponse.json().catch(() => ({detail: "Failed to remove bookmark"}));
                        throw new Error(errorData.detail || 'Failed to remove bookmark');
                    }
                    showMessage('success', 'Bookmark removed.');
                    loadBookmarkedArticles(); 
                } catch (error) {
                    console.error("Error removing bookmark:", error);
                    showMessage('error', `Could not remove bookmark: ${error.message}`);
                }
            });
        });

    } catch (error) {
        console.error("Error loading bookmarks:", error);
        bookmarksListDiv.innerHTML = `<div class="error">Could not load bookmarks: ${error.message}</div>`;
    }
}

// --- MeSH Terms Tab Logic ---
async function renderMeshTab() {
    const contentPlaceholder = document.getElementById('content-placeholder');
    if (!contentPlaceholder) { console.error("renderMeshTab: contentPlaceholder not found"); return; }
    contentPlaceholder.innerHTML = `
        <h2>MeSH Terms Management</h2>
        <div class="form-group">
            <label for="newMeshTerm">Add New MeSH Term (Manual Entry):</label>
            <input type="text" id="newMeshTerm" name="newMeshTerm" placeholder="e.g., Medical Education">
            <button id="addMeshButton" style="margin-left: 10px; padding: 10px 15px; vertical-align: bottom;">Add Term</button>
        </div>
        <div class="form-group" style="margin-top: 10px;">
            <button id="restoreDefaultMeshButton" style="padding: 10px 15px;">Restore Default MeSH Terms</button>
        </div>
        <hr style="margin: 20px 0;">
        <h3><a href="https://meshb.nlm.nih.gov/treeView" target="_blank" rel="noopener noreferrer">Browse MeSH Tree Terms</a></h3>
        <p>Click the link above to open the official MeSH browser in a new tab. You can copy-paste terms from there into the text box above. Ignore any alphanumeric descriptors in square brackets such as [D03.066.288.478]</p>
        <h3 style="margin-top: 30px;">Current MeSH Terms (Selected):</h3>
        <ul id="meshList" style="list-style-type: none; padding-left: 0;"></ul>`;

    await loadMeshTerms(); 
    const addMeshBtn = document.getElementById('addMeshButton');
    if(addMeshBtn) addMeshBtn.addEventListener('click', () => handleAddMeshTerm()); // Ensure it calls without args for manual input

    const restoreDefaultsBtn = document.getElementById('restoreDefaultMeshButton');
    if(restoreDefaultsBtn) restoreDefaultsBtn.addEventListener('click', handleRestoreDefaultMeshTerms);
}

async function loadMeshTerms() {
    const meshList = document.getElementById('meshList');
    if (!meshList) { console.error("loadMeshTerms: meshList element not found."); return;}
    meshList.innerHTML = '<li><div class="loading">Loading MeSH terms...</div></li>';
    try {
        const response = await fetch('/api/mesh-terms');
        if (!response.ok) throw new Error('Failed to fetch MeSH terms');
        const terms = await response.json(); // Expects List[MeSHTermResponse] which is List[{id:str, term:str}]

        meshList.innerHTML = ''; 
        if (terms.length === 0) {
            meshList.innerHTML = '<li>No MeSH terms found. Add some!</li>';
            return;
        }

        terms.forEach(term => { // term is {id: string, term: string}
            const listItem = document.createElement('li');
            Object.assign(listItem.style, { marginBottom: '8px', padding: '8px', border: '1px solid #eee', borderRadius: '4px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' });
            
            const termText = document.createElement('span');
            termText.textContent = term.term;
            listItem.appendChild(termText);

            const deleteButton = document.createElement('button');
            deleteButton.textContent = 'Delete';
            Object.assign(deleteButton.style, { backgroundColor: '#dc3545', color: 'white', border: 'none', padding: '5px 10px', borderRadius: '4px', cursor: 'pointer' });
            deleteButton.onclick = () => handleDeleteMeshTerm(term.id, term.term); 
            listItem.appendChild(deleteButton);
            
            meshList.appendChild(listItem);
        });
    } catch (error) {
        console.error("Error loading MeSH terms:", error);
        meshList.innerHTML = `<li><div class="error">Could not load MeSH terms: ${error.message}</div></li>`;
    }
}

// MODIFIED: handleAddMeshTerm to check for duplicates and accept parameters
async function handleAddMeshTerm(termToAdd = null, isBatchAdd = false) {
    const newMeshTermInput = document.getElementById('newMeshTerm');
    const term = termToAdd ? termToAdd.trim() : (newMeshTermInput ? newMeshTermInput.value.trim() : '');

    if (!term) {
        if (!isBatchAdd) { // Only show error if it's a manual single add
            showMessage('error', 'MeSH term cannot be empty.');
        }
        return { success: false, reason: 'empty' };
    }

    // Fetch current terms to check for duplicates
    const currentMeshTermsStrings = await fetchUserMeshTerms(); // This returns an array of strings
    const termLower = term.toLowerCase();
    if (currentMeshTermsStrings.some(existingTerm => existingTerm.toLowerCase() === termLower)) {
        if (!isBatchAdd) {
            showMessage('info', `MeSH term "${term}" already exists.`);
        }
        return { success: false, reason: 'duplicate', term: term };
    }

    if (!isBatchAdd) {
        showMessage('loading', `Adding MeSH term "${term}"...`, 0);
    }

    try {
        const response = await fetch('/api/mesh-terms', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', },
            body: JSON.stringify({ term: term }),
        });
        const responseData = await response.json(); 
        if (!response.ok) {
            let errorMessage = responseData.detail || `Failed to add MeSH term. Status: ${response.status}`;
            if (response.status === 409) { 
                 errorMessage = responseData.detail || `MeSH term '${term}' already exists (backend check).`;
            }
            throw new Error(errorMessage);
        }
        
        if (!isBatchAdd) {
            showMessage('success', `MeSH term "${term}" added successfully!`);
            if (newMeshTermInput) newMeshTermInput.value = ''; 
        }
        if (!isBatchAdd) { // Only reload if it's a single add, batch add will reload once at the end.
             await loadMeshTerms();
        }
        return { success: true, term: term };
    } catch (error) {
        console.error("Error adding MeSH term:", error);
        if (!isBatchAdd) {
            showMessage('error', `Could not add MeSH term "${term}": ${error.message}`);
        }
        return { success: false, reason: 'error', message: error.message, term: term };
    }
}

// NEW FUNCTION: To handle restoring default MeSH terms
async function handleRestoreDefaultMeshTerms() {
    showMessage('loading', 'Restoring default MeSH terms...', 0);
    const currentMeshTerms = await fetchUserMeshTerms(); // Array of strings
    const currentMeshTermsLower = currentMeshTerms.map(t => t.toLowerCase());
    
    let addedCount = 0;
    let skippedCount = 0;
    let errorCount = 0;

    for (const defaultTerm of DEFAULT_MESH_TERMS) {
        if (!currentMeshTermsLower.includes(defaultTerm.toLowerCase())) {
            const result = await handleAddMeshTerm(defaultTerm, true); // true for isBatchAdd
            if (result.success) {
                addedCount++;
            } else if (result.reason !== 'duplicate') { // Don't count backend-confirmed duplicates as errors here, already checked
                errorCount++;
                console.error(`Error adding default term "${defaultTerm}": ${result.message || result.reason}`);
            } else {
                // This case should ideally be caught by the frontend check, but good to have as a fallback
                skippedCount++; 
            }
        } else {
            skippedCount++;
        }
    }

    await loadMeshTerms(); // Refresh the list once after all attempts

    let summaryMessage = '';
    if (addedCount > 0) {
        summaryMessage += `${addedCount} default MeSH term(s) added. `;
    }
    if (skippedCount > 0) {
        summaryMessage += `${skippedCount} already existed or were skipped. `;
    }
    if (errorCount > 0) {
        summaryMessage += `${errorCount} failed to add.`;
    }

    if (addedCount === 0 && skippedCount > 0 && errorCount === 0) {
        summaryMessage = 'All default MeSH terms already exist in your list.';
    } else if (summaryMessage === '') {
        summaryMessage = 'No default terms processed or an unexpected issue occurred.';
    }

    showMessage('success', summaryMessage.trim(), 5000);
}

// NEW FUNCTION: To re-add a MeSH term after an "Undo"
async function reAddMeshTerm(termName) {
    if (!termName) {
        console.error("reAddMeshTerm: termName is empty.");
        showMessage('error', 'Cannot restore term: Name is missing.');
        return;
    }

    // Using showNotification for consistency with other transient messages, or showMessage if preferred
    showNotification(`Restoring term "${termName}"...`, 2000); // Brief message
    try {
        const response = await fetch('/api/mesh-terms', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ term: termName }),
        });
        const responseData = await response.json(); // Attempt to parse JSON for all responses
        if (!response.ok) {
            let errorMessage = responseData.detail || `Failed to restore MeSH term. Status: ${response.status}`;
            // Check for 409 Conflict (already exists) specifically
            if (response.status === 409) { 
                errorMessage = responseData.detail || `MeSH term '${termName}' may already exist.`;
            }
            throw new Error(errorMessage);
        }
        
        // Successful restoration, no explicit success message needed here as list will refresh.
        // showNotification(`Term "${termName}" restored!`, 3000);
        await loadMeshTerms(); // Refresh the list to show the restored term
    } catch (error) {
        console.error("Error restoring MeSH term:", error);
        showNotification(`Could not restore: ${error.message}`, 4000); // Show error
        // Optionally, refresh list even on error to reflect actual backend state
        await loadMeshTerms();
    }
}

// MODIFIED FUNCTION: handleDeleteMeshTerm
async function handleDeleteMeshTerm(termId, termName) { // Added termName parameter
    // REMOVED confirm dialog

    // showMessage('loading', `Deleting term "${termName}"...`, 0); // Can be too quick to notice

    try {
        const response = await fetch(`/api/mesh-terms/${termId}`, { 
            method: 'DELETE',
        });

        if (!response.ok) {
            let backendErrorMsg = 'Failed to delete MeSH term.'; // Default message
            try {
                // Attempt to parse the JSON body of the error response
                const errorData = await response.json();
                if (errorData && errorData.detail) {
                    if (Array.isArray(errorData.detail) && errorData.detail.length > 0) {
                        // Handle FastAPI validation errors (list of error objects)
                        backendErrorMsg = errorData.detail.map(err => err.msg || JSON.stringify(err)).join('; ');
                    } else if (typeof errorData.detail === 'string') {
                        // Handle simple string detail messages
                        backendErrorMsg = errorData.detail;
                    } else if (typeof errorData.detail === 'object') {
                        // Handle other object-based detail messages
                        backendErrorMsg = JSON.stringify(errorData.detail);
                    }
                } else if (response.statusText) {
                    // Fallback to HTTP status text if no detail in JSON
                    backendErrorMsg = `Server error: ${response.status} ${response.statusText}`;
                }
            } catch (e) {
                // If JSON parsing fails or another error occurs, use status text or a generic message
                backendErrorMsg = response.statusText || 'Unknown error occurred while processing the deletion response.';
                console.warn('Could not parse error response JSON for MeSH term deletion:', e);
            }
            console.log('[handleDeleteMeshTerm] backendErrorMsg before throw:', backendErrorMsg, typeof backendErrorMsg); // Enhanced logging
            throw new Error(backendErrorMsg); // This error will be caught by the outer catch block
        }
        
        // Backend deletion successful
        await loadMeshTerms(); // Refresh the list immediately to show the term as gone

        // Show "Term deleted" with Undo option
        showNotificationWithUndo(`Term "${termName}" deleted.`, () => {
            reAddMeshTerm(termName); // Pass the term name to the re-add function
        }); // Uses default duration from showNotificationWithUndo (e.g., 7s)
        
    } catch (error) { // Outer catch block for the fetch operation or the explicitly thrown error
        console.error(`[handleDeleteMeshTerm] Error deleting MeSH term ${termName} (ID: ${termId}). Full error object:`, error); // Log the full error object
        
        let displayErrorMessage = 'An unexpected error occurred. Check console for details.';
        if (error && error.message && typeof error.message === 'string' && error.message.toLowerCase() !== '[object object]') {
            displayErrorMessage = error.message;
        } else if (typeof error === 'string') { // Fallback if error itself is a string
            displayErrorMessage = error;
        } else if (error && error.toString && typeof error.toString === 'function' && error.toString().toLowerCase() !== '[object object]') {
            displayErrorMessage = error.toString(); // Try toString() as a last resort for a meaningful message
        }
        console.log(`[handleDeleteMeshTerm] Message being shown to user for delete error:`, displayErrorMessage);

        showNotification(`Could not delete "${termName}": ${displayErrorMessage}`, 5000);
        await loadMeshTerms(); // Refresh list to show current state even on error
    }
}

// --- MeSH Tree Browsing Logic --- 
// (Using placeholder stubs for brevity as this section was largely okay before)
// Ensure the full, correct MeSH tree functions are in the actual file if these stubs cause issues.

function sanitizeText(text) {
    if (!text) return "";
    // Basic sanitization: remove HTML tags. More robust sanitization might be needed.
    const MESH_HTML_REGEX = /<[^>]*>?/gm;
    const sanitized = text.replace(MESH_HTML_REGEX, '');
    // Basic entity decoding, expand if more are common in MeSH data
    return sanitized
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&amp;/g, '&')
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'")
        .replace(/&nbsp;/g, ' ');
}

async function initMeshTree() { 
    const treeContainer = document.getElementById('meshTreeViewContainer');
    const treeStatus = document.getElementById('meshTreeStatus');
    if (!treeContainer || !treeStatus) { console.warn("MeSH tree container or status element not found."); return; }
    treeContainer.innerHTML = '<div class="loading">Loading MeSH categories...</div>';
    treeStatus.innerHTML = ''; // Clear previous status
    await fetchAndDisplayMeshRoot(treeContainer, treeStatus);
}

async function fetchAndDisplayMeshRoot(treeContainer, treeStatus) {
    try {
        const cachedRootNodes = meshTreeCache.get('root');
        let rootNodes;
        if (cachedRootNodes) {
            rootNodes = cachedRootNodes;
            if (treeStatus) treeStatus.innerHTML = '<div class="info" style="font-size:0.8em; margin-bottom:5px;">Showing cached MeSH categories. <button id="resetMeshCacheBtn" style="font-size:0.8em; padding: 2px 5px; margin-left:5px;">Reset Cache</button></div>';
            const resetBtn = document.getElementById('resetMeshCacheBtn');
            if(resetBtn) resetBtn.onclick = () => { meshTreeCache.clear(); initMeshTree(); };
        } else {
            const response = await fetch('/api/mesh/tree/root');
            if (!response.ok) {
                const errData = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
                throw new Error(errData.detail || 'Failed to load root MeSH categories');
            }
            rootNodes = await response.json();
            meshTreeCache.set('root', rootNodes);
            if (treeStatus) treeStatus.innerHTML = ''; 
        }
        
        treeContainer.innerHTML = ''; // Clear loading/previous content
        if (rootNodes.length === 0) {
            treeContainer.innerHTML = '<p>No top-level MeSH categories found.</p>';
            return;
        }
        const ul = document.createElement('ul');
        ul.style.listStyleType = 'none';
        ul.style.paddingLeft = '0';
        rootNodes.forEach(nodeData => {
            ul.appendChild(createMeshTreeNodeElement(nodeData, 0));
        });
        treeContainer.appendChild(ul);
    } catch (error) {
        console.error("Error fetching root MeSH categories:", error);
        if (treeStatus) treeStatus.innerHTML = `<div class="error">${error.message}</div>`;
        treeContainer.innerHTML = '<p class="error">Could not load MeSH tree.</p>'; 
    }
}

function createMeshTreeNodeElement(nodeData, depth = 0) {
    const name = nodeData.name || "Unnamed Node";
    if (name.includes('<') || name.includes('>')) { // Basic check for HTML in name
        console.warn("Skipping MeSH node with potential HTML in name:", name);
        const emptyLi = document.createElement('li');
        emptyLi.style.display = 'none'; // Hide problematic nodes
        return emptyLi;
    }
    
    const li = document.createElement('li');
    const nodeContainer = document.createElement('div');
    nodeContainer.classList.add('mesh-node');
    nodeContainer.style.marginLeft = `${depth * 20}px`;
    nodeContainer.dataset.treePrefix = nodeData.tree_prefix; // Store for fetching children
    nodeContainer.dataset.meshName = name;
    nodeContainer.dataset.meshUI = nodeData.mesh_ui || '';

    if (nodeData.has_children) {
        const expander = document.createElement('span');
        expander.classList.add('tree-expander');
        expander.textContent = '+'; 
        expander.title = 'Expand/Collapse';
        expander.style.cursor = 'pointer';
        expander.style.marginRight = '5px';
        nodeContainer.appendChild(expander);
        
        expander.onclick = function(e) {
            e.stopPropagation();
            const childrenUList = li.querySelector('ul.mesh-children');
            if (childrenUList) { // Should always exist if has_children is true
                const isHidden = childrenUList.style.display === 'none';
                if (isHidden) {
                    if (childrenUList.children.length === 0) { // Not yet loaded
                        fetchAndDisplayMeshChildren(nodeData.tree_prefix, childrenUList, depth, expander);
                    }
                    childrenUList.style.display = 'block';
                    expander.textContent = '−';
                } else {
                    childrenUList.style.display = 'none';
                    expander.textContent = '+';
                }
            }
        };
    }
    
    const label = document.createElement('span');
    label.classList.add('mesh-term-name');
    label.textContent = sanitizeText(name);
    nodeContainer.appendChild(label);
    
    if (nodeData.has_add_button) { // Assuming backend provides this boolean
        const addButton = document.createElement('button');
        addButton.classList.add('btn', 'btn-sm', 'btn-add-mesh-from-tree'); 
        addButton.textContent = 'Add';
        addButton.setAttribute('type', 'button');
        addButton.title = 'Add this term to your search list';
        addButton.style.marginLeft = '10px';
        addButton.style.padding = '2px 6px';
        addButton.addEventListener('click', function(e) {
            e.stopPropagation();
            addMeshTermFromTree(sanitizeText(name)); // meshUI is not directly used by addMeshTermFromTree
        });
        nodeContainer.appendChild(addButton);
    }
    
    li.appendChild(nodeContainer);
    
    if (nodeData.has_children) { // Pre-create ul for children
        const childrenUList = document.createElement('ul');
        childrenUList.classList.add('mesh-children');
        childrenUList.style.display = 'none'; 
        childrenUList.style.paddingLeft = '0px'; // No extra indent from ul itself
        li.appendChild(childrenUList);
    }
    return li;
}

async function fetchAndDisplayMeshChildren(treePrefix, childrenUList, depth, expanderElement) {
    if (!childrenUList) { console.error("fetchAndDisplayMeshChildren: childrenUList is null"); return; }
    
    const cachedChildren = meshTreeCache.get(treePrefix);
    if (cachedChildren) {
        renderMeshChildren(cachedChildren, childrenUList, depth);
        return; // Already rendered if cached
    }
    
    childrenUList.innerHTML = `<li><div class="loading" style="padding-left: ${ (depth + 1) * 20 }px;">Loading children...</div></li>`;
    try {
        const response = await fetch(`/api/mesh/tree/children/${encodeURIComponent(treePrefix)}`);
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Failed to load children' }));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        const children = await response.json();
        meshTreeCache.set(treePrefix, children);
        renderMeshChildren(children, childrenUList, depth);
    } catch (error) {
        console.error(`Error fetching MeSH children for ${treePrefix}:`, error);
        childrenUList.innerHTML = `<li><div class="error" style="padding-left: ${ (depth + 1) * 20 }px;">Failed to load: ${error.message}</div></li>`;
        if (expanderElement) expanderElement.textContent = "+"; // Reset expander if load fails
    }
}

function renderMeshChildren(children, childrenUList, depth) {
    if (!childrenUList) { console.error("renderMeshChildren: childrenUList is null"); return; }
    childrenUList.innerHTML = ''; // Clear loading/previous
    
    const sanitizedChildren = children.filter(child => {
        const name = child.name || "";
        if (name.includes('<') || name.includes('>')) return false;
        if (!child.tree_prefix || !child.name) return false;
        return true;
    });
    
    if (sanitizedChildren.length === 0) {
        childrenUList.innerHTML = `<li style="list-style-type:none; margin-left:${ (depth + 1) * 20 }px;"><div class="note">No sub-terms found.</div></li>`;
        return;
    }
    sanitizedChildren.forEach(childNode => {
        childrenUList.appendChild(createMeshTreeNodeElement(childNode, depth + 1));
    });
}

async function addMeshTermFromTree(termName) { // meshUi not directly used, adds by name
    // This function simulates adding a term as if typed manually.
    // It reuses handleAddMeshTerm by temporarily setting the input field's value.
    const newMeshTermInput = document.getElementById('newMeshTerm');
    let originalValue = '';
    if (newMeshTermInput) {
        originalValue = newMeshTermInput.value;
        newMeshTermInput.value = termName; // Set term to be added
    }
    
    await handleAddMeshTerm(); // Call the existing logic for adding a term
    
    if (newMeshTermInput) { // Restore original value if any
        newMeshTermInput.value = originalValue;
    }
}


// --- Settings Tab Logic ---
async function renderSettingsTab() {
    const contentPlaceholder = document.getElementById('content-placeholder');
    if (!contentPlaceholder) { console.error("renderSettingsTab: contentPlaceholder not found"); return; }
    contentPlaceholder.innerHTML = `
        <h2>Settings</h2>
        <div class="form-group">
            <label for="entrezEmail">Entrez Email:</label>
            <input type="email" id="entrezEmail" name="entrezEmail" placeholder="your.email@example.com">
            <p class="note">Required by NCBI for PubMed API access.</p>
        </div>
        <div class="form-group">
            <label for="pubmedApiKey">PubMed API Key (Optional):</label>
            <input type="text" id="pubmedApiKey" name="pubmedApiKey" placeholder="Optional API Key">
            <p class="note">Recommended for frequent use to avoid rate limiting.</p>
        </div>
        <div class="form-actions"><button id="saveSettingsButton">Save Settings</button></div>`;

    try {
        const response = await fetch('/api/config');
        if (!response.ok) throw new Error('Failed to fetch settings');
        const config = await response.json();
        const entrezEmailInput = document.getElementById('entrezEmail');
        const pubmedApiKeyInput = document.getElementById('pubmedApiKey');
        if (entrezEmailInput) entrezEmailInput.value = config.entrez_email || '';
        if (pubmedApiKeyInput) {
            if (config.pubmed_api_key && config.pubmed_api_key.toLowerCase() !== 'your_pubmed_api_key_here') {
                pubmedApiKeyInput.value = config.pubmed_api_key;
            } else {
                pubmedApiKeyInput.value = ''; // Ensure placeholder shows if it's the placeholder string or empty
            }
        }
    } catch (error) {
        console.error("Error fetching settings:", error);
        showMessage('error', `Could not load settings: ${error.message}`);
    }

    const saveButton = document.getElementById('saveSettingsButton');
    if (saveButton) saveButton.addEventListener('click', saveSettings);
}

async function saveSettings() {
    const emailInput = document.getElementById('entrezEmail');
    const apiKeyInput = document.getElementById('pubmedApiKey');
    
    const email = emailInput ? emailInput.value : '';
    const apiKey = apiKeyInput ? apiKeyInput.value : '';

    if (!email) {
        showMessage('error', 'Entrez Email is required.');
        return;
    }

    showMessage('loading', 'Saving settings...', 0); 

    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', },
            body: JSON.stringify({ entrez_email: email, pubmed_api_key: apiKey }),
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({detail: "Failed to save settings."}));
            throw new Error(errorData.detail || 'Failed to save settings');
        }
        const updatedConfig = await response.json();
        showMessage('success', 'Settings saved successfully!');
        if (emailInput) emailInput.value = updatedConfig.entrez_email || '';
        if (apiKeyInput) apiKeyInput.value = updatedConfig.pubmed_api_key || '';

    } catch (error) {
        console.error("Error saving settings:", error);
        showMessage('error', `Could not save settings: ${error.message}`);
    }
}

// Refactored DOMContentLoaded listener with diagnostic logging
document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM fully loaded and parsed. Frontend app can initialize. (v3 full restore)");
    const tabButtons = document.querySelectorAll('.tab-buttons button');
    const contentPlaceholder = document.getElementById('content-placeholder');

    if (!tabButtons.length) {
        console.error("No tab buttons found. Tab system cannot initialize.");
        if (contentPlaceholder) contentPlaceholder.innerHTML = "<p>Error: Tab navigation buttons not found.</p>";
        return;
    }
    if (!contentPlaceholder) {
        console.error("Content placeholder element not found. Tab system cannot initialize.");
        return;
    }
    console.log(`Found ${tabButtons.length} tab buttons and content placeholder.`);

    const tabActionMap = {
        'search-articles': renderSearchArticlesTab,
        'journal-rankings': renderJournalRankingsTab,
        'mesh-terms': renderMeshTab,
        'bookmarks': renderBookmarksTab,
        'settings': renderSettingsTab,
    };
    // Log keys to check if functions are defined by this point
    console.log("Tab action map created. Functions available:", 
        Object.keys(tabActionMap).reduce((acc, key) => {
            acc[key] = typeof tabActionMap[key] === 'function';
            return acc;
        }, {})
    );


    tabButtons.forEach(button => {
        button.addEventListener('click', (event) => {
            const tabButton = event.currentTarget;
            const tabId = tabButton.dataset.tab;
            console.log(`Tab button clicked: id='${tabId}'`);
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabButton.classList.add('active');
            console.log(`'${tabId}' tab marked active.`);
            console.log(`Clearing content placeholder for tab: '${tabId}'`);
            contentPlaceholder.innerHTML = '';
            if (tabActionMap[tabId]) {
                console.log(`Calling render function for tab: '${tabId}'`);
                try {
                    tabActionMap[tabId](); // Execute the function
                    console.log(`Render function for tab '${tabId}' called successfully.`);
                } catch (e) {
                    console.error(`Error rendering tab '${tabId}':`, e);
                    contentPlaceholder.innerHTML = `<p>Error loading content for <strong>${tabId}</strong>. Check console.</p>`;
                }
            } else {
                console.warn(`No action defined in tabActionMap for tab: '${tabId}'`);
                contentPlaceholder.innerHTML = `<p>Content for <strong>${tabId}</strong> is under construction (no action defined).</p>`;
            }
        });
    });

    console.log("Attempting to load initial tab...");
    let initialTabButton = document.querySelector('.tab-buttons button[data-tab="journal-rankings"]');
    if (!initialTabButton && tabButtons.length > 0) {
        console.log("Journal rankings tab button not found, falling back to first tab button.");
        initialTabButton = tabButtons[0];
    }

    if (initialTabButton) {
        console.log("Initial tab to load found:", initialTabButton.dataset.tab);
        initialTabButton.click(); // Dispatch click to trigger tab loading logic
        console.log("Initial tab click event dispatched.");
    } else {
        console.warn("No initial tab could be determined or clicked.");
        contentPlaceholder.innerHTML = '<p>Select a tab to begin. (No initial tab found)</p>';
    }
}); 