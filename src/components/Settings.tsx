import React, { useState } from 'react';
import { useQuery, useMutation } from 'react-query';
import axios from 'axios';

interface Config {
  entrez_email: string;
  pubmed_api_key: string;
}

function Settings() {
  const [config, setConfig] = useState<Config>({
    entrez_email: '',
    pubmed_api_key: ''
  });

  const { data: currentConfig, isLoading } = useQuery<Config>(
    'config',
    async () => {
      const response = await axios.get('/api/config');
      return response.data;
    },
    {
      onSuccess: (data) => {
        setConfig(data);
      }
    }
  );

  const updateConfig = useMutation(
    async (newConfig: Config) => {
      const response = await axios.post('/api/config', newConfig);
      return response.data;
    },
    {
      onSuccess: (data) => {
        setConfig(data);
      }
    }
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateConfig.mutate(config);
  };

  if (isLoading) {
    return (
      <div className="bg-white shadow rounded-lg p-6">
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-2 text-gray-600">Loading settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white shadow rounded-lg p-6">
      <h2 className="text-xl font-semibold mb-6">Settings</h2>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Entrez Email
          </label>
          <input
            type="email"
            value={config.entrez_email}
            onChange={(e) => setConfig({ ...config, entrez_email: e.target.value })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            placeholder="your.email@example.com"
          />
          <p className="mt-1 text-sm text-gray-500">
            Required for PubMed API access
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">
            PubMed API Key
          </label>
          <input
            type="password"
            value={config.pubmed_api_key}
            onChange={(e) => setConfig({ ...config, pubmed_api_key: e.target.value })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            placeholder="Your PubMed API key"
          />
          <p className="mt-1 text-sm text-gray-500">
            Optional: Increases rate limits for PubMed API
          </p>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            className="bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600"
            disabled={updateConfig.isLoading}
          >
            {updateConfig.isLoading ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </form>
    </div>
  );
}

export default Settings;