import React from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import axios from 'axios';

interface Bookmark {
  pmid: string;
  title: string;
  authors: string;
  journal: string;
  pub_date: string;
  abstract: string;
  timestamp: string;
}

function Bookmarks() {
  const queryClient = useQueryClient();

  const { data: bookmarks, isLoading, error } = useQuery<Bookmark[]>(
    'bookmarks',
    async () => {
      const response = await axios.get('/api/bookmarked-articles');
      return response.data.bookmarks;
    }
  );

  const removeBookmark = useMutation(
    async (pmid: string) => {
      await axios.delete(`/api/bookmark-article/${pmid}`);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries('bookmarks');
      }
    }
  );

  return (
    <div className="bg-white shadow rounded-lg p-6">
      <h2 className="text-xl font-semibold mb-6">Bookmarked Articles</h2>

      {isLoading && (
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-2 text-gray-600">Loading bookmarks...</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-red-600">Error loading bookmarks. Please try again.</p>
        </div>
      )}

      {bookmarks && bookmarks.length === 0 && (
        <p className="text-gray-500 text-center py-4">No bookmarked articles yet.</p>
      )}

      {bookmarks && bookmarks.length > 0 && (
        <div className="space-y-6">
          {bookmarks.map((bookmark) => (
            <div key={bookmark.pmid} className="border-b pb-4">
              <h3 className="text-lg font-medium text-blue-600">
                <a
                  href={`https://pubmed.ncbi.nlm.nih.gov/${bookmark.pmid}/`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {bookmark.title}
                </a>
              </h3>
              <p className="text-sm text-gray-600 mt-1">{bookmark.authors}</p>
              <p className="text-sm text-gray-500 mt-1">
                {bookmark.journal} • {bookmark.pub_date}
              </p>
              {bookmark.abstract && (
                <p className="text-gray-700 mt-2">{bookmark.abstract}</p>
              )}
              <div className="mt-2 flex justify-end">
                <button
                  onClick={() => removeBookmark.mutate(bookmark.pmid)}
                  className="text-red-600 hover:text-red-800 text-sm"
                  disabled={removeBookmark.isLoading}
                >
                  Remove Bookmark
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Bookmarks;