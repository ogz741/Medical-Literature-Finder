import React, { useState } from 'react';
import { useQuery } from 'react-query';
import axios from 'axios';
import { format } from 'date-fns';

interface SearchParams {
  journal_specialty: string;
  selected_journals: string[];
  start_date: string;
  end_date: string;
  mesh_terms: string[];
  max_journals_to_search: number;
  max_articles_per_journal: number;
}

interface Article {
  pubmed_id: string;
  title: string;
  journal: string;
  publication_date: string;
  authors: string[];
  mesh_terms: string[];
  abstract: string;
  url: string;
  impact_factor: number;
}

function SearchArticles() {
  const [searchParams, setSearchParams] = useState<SearchParams>({
    journal_specialty: 'Ophthalmology',
    selected_journals: [],
    start_date: format(new Date().setMonth(new Date().getMonth() - 1), 'yyyy-MM-dd'),
    end_date: format(new Date(), 'yyyy-MM-dd'),
    mesh_terms: [],
    max_journals_to_search: 5,
    max_articles_per_journal: 10
  });

  const [selectedFormat, setSelectedFormat] = useState<string>('');

  const { data: articles, isLoading, error, refetch } = useQuery<Article[]>(
    ['articles', searchParams],
    async () => {
      const response = await axios.post('/api/search-articles', searchParams);
      return response.data;
    },
    { enabled: false }
  );

  const handleSearch = () => {
    refetch();
  };

  const handleDownload = async (format: string) => {
    try {
      const response = await axios.post(
        `/api/download-search-results`,
        {
          ...searchParams,
          format,
          max_results: 500
        },
        { responseType: 'blob' }
      );

      const url = window.URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = `medical-articles.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Search Parameters</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Specialty</label>
            <select
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              value={searchParams.journal_specialty}
              onChange={(e) => setSearchParams(prev => ({ ...prev, journal_specialty: e.target.value }))}
            >
              <option value="Ophthalmology">Ophthalmology</option>
              <option value="Dermatology">Dermatology</option>
              <option value="Cardiology">Cardiology</option>
              {/* Add more specialties */}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Date Range</label>
            <div className="flex space-x-2">
              <input
                type="date"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                value={searchParams.start_date}
                onChange={(e) => setSearchParams(prev => ({ ...prev, start_date: e.target.value }))}
              />
              <input
                type="date"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                value={searchParams.end_date}
                onChange={(e) => setSearchParams(prev => ({ ...prev, end_date: e.target.value }))}
              />
            </div>
          </div>
        </div>

        <div className="mt-4">
          <button
            className="bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600"
            onClick={handleSearch}
          >
            Search Articles
          </button>
        </div>
      </div>

      {isLoading && (
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-2 text-gray-600">Searching articles...</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-red-600">Error loading articles. Please try again.</p>
        </div>
      )}

      {articles && articles.length > 0 && (
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">Search Results</h2>
            <div className="flex space-x-2">
              <select
                className="rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                value={selectedFormat}
                onChange={(e) => setSelectedFormat(e.target.value)}
              >
                <option value="">Select format...</option>
                <option value="pdf">PDF</option>
                <option value="csv">CSV</option>
                <option value="xlsx">Excel</option>
                <option value="bibtex">BibTeX</option>
              </select>
              <button
                className="bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600 disabled:opacity-50"
                disabled={!selectedFormat}
                onClick={() => handleDownload(selectedFormat)}
              >
                Download
              </button>
            </div>
          </div>

          <div className="space-y-6">
            {articles.map((article) => (
              <div key={article.pubmed_id} className="border-b pb-4">
                <h3 className="text-lg font-medium text-blue-600">
                  <a href={article.url} target="_blank" rel="noopener noreferrer">
                    {article.title}
                  </a>
                </h3>
                <p className="text-sm text-gray-600 mt-1">
                  {article.authors.join(', ')}
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  {article.journal} • {article.publication_date} • Impact Factor: {article.impact_factor}
                </p>
                {article.abstract && (
                  <p className="text-gray-700 mt-2">{article.abstract}</p>
                )}
                {article.mesh_terms && article.mesh_terms.length > 0 && (
                  <div className="mt-2">
                    <p className="text-sm text-gray-500">MeSH Terms:</p>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {article.mesh_terms.map((term) => (
                        <span
                          key={term}
                          className="inline-block bg-gray-100 rounded-full px-3 py-1 text-sm text-gray-700"
                        >
                          {term}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default SearchArticles;