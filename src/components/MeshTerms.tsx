import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import axios from 'axios';

interface MeshTerm {
  id: string;
  term: string;
}

function MeshTerms() {
  const [newTerm, setNewTerm] = useState('');
  const queryClient = useQueryClient();

  const { data: meshTerms, isLoading, error } = useQuery<MeshTerm[]>(
    'mesh-terms',
    async () => {
      const response = await axios.get('/api/mesh-terms');
      return response.data;
    }
  );

  const addMeshTerm = useMutation(
    async (term: string) => {
      const response = await axios.post('/api/mesh-terms', { term });
      return response.data;
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries('mesh-terms');
        setNewTerm('');
      }
    }
  );

  const deleteMeshTerm = useMutation(
    async (termId: string) => {
      await axios.delete(`/api/mesh-terms/${termId}`);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries('mesh-terms');
      }
    }
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (newTerm.trim()) {
      addMeshTerm.mutate(newTerm.trim());
    }
  };

  return (
    <div className="bg-white shadow rounded-lg p-6">
      <h2 className="text-xl font-semibold mb-6">MeSH Terms</h2>

      <form onSubmit={handleSubmit} className="mb-6">
        <div className="flex gap-2">
          <input
            type="text"
            value={newTerm}
            onChange={(e) => setNewTerm(e.target.value)}
            placeholder="Enter new MeSH term"
            className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          />
          <button
            type="submit"
            className="bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600"
            disabled={addMeshTerm.isLoading}
          >
            Add Term
          </button>
        </div>
      </form>

      {isLoading && (
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-2 text-gray-600">Loading MeSH terms...</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-red-600">Error loading MeSH terms. Please try again.</p>
        </div>
      )}

      {meshTerms && (
        <div className="space-y-2">
          {meshTerms.map((term) => (
            <div
              key={term.id}
              className="flex justify-between items-center p-3 bg-gray-50 rounded-md"
            >
              <span className="text-gray-700">{term.term}</span>
              <button
                onClick={() => deleteMeshTerm.mutate(term.id)}
                className="text-red-600 hover:text-red-800"
                disabled={deleteMeshTerm.isLoading}
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default MeshTerms;