import React, { useState } from 'react'
import { QueryClient, QueryClientProvider } from 'react-query'
import SearchArticles from './components/SearchArticles'
import JournalRankings from './components/JournalRankings'
import MeshTerms from './components/MeshTerms'
import Bookmarks from './components/Bookmarks'
import Settings from './components/Settings'

const queryClient = new QueryClient()

function App() {
  const [activeTab, setActiveTab] = useState('search-articles')

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex items-center space-x-4">
              <img 
                src="https://images.pexels.com/photos/4386466/pexels-photo-4386466.jpeg?auto=compress&w=32" 
                alt="Logo" 
                className="w-8 h-8 rounded-full"
              />
              <h1 className="text-2xl font-bold text-gray-900">Medical Literature Finder</h1>
            </div>
            <nav className="mt-4">
              <div className="flex space-x-4">
                <button
                  onClick={() => setActiveTab('search-articles')}
                  className={`px-3 py-2 rounded-md text-sm font-medium ${
                    activeTab === 'search-articles'
                      ? 'bg-blue-500 text-white'
                      : 'text-gray-500 hover:bg-gray-100'
                  }`}
                >
                  Search Articles
                </button>
                <button
                  onClick={() => setActiveTab('journal-rankings')}
                  className={`px-3 py-2 rounded-md text-sm font-medium ${
                    activeTab === 'journal-rankings'
                      ? 'bg-blue-500 text-white'
                      : 'text-gray-500 hover:bg-gray-100'
                  }`}
                >
                  Journal Rankings
                </button>
                <button
                  onClick={() => setActiveTab('mesh-terms')}
                  className={`px-3 py-2 rounded-md text-sm font-medium ${
                    activeTab === 'mesh-terms'
                      ? 'bg-blue-500 text-white'
                      : 'text-gray-500 hover:bg-gray-100'
                  }`}
                >
                  MeSH Terms
                </button>
                <button
                  onClick={() => setActiveTab('bookmarks')}
                  className={`px-3 py-2 rounded-md text-sm font-medium ${
                    activeTab === 'bookmarks'
                      ? 'bg-blue-500 text-white'
                      : 'text-gray-500 hover:bg-gray-100'
                  }`}
                >
                  Bookmarks
                </button>
                <button
                  onClick={() => setActiveTab('settings')}
                  className={`px-3 py-2 rounded-md text-sm font-medium ${
                    activeTab === 'settings'
                      ? 'bg-blue-500 text-white'
                      : 'text-gray-500 hover:bg-gray-100'
                  }`}
                >
                  Settings
                </button>
              </div>
            </nav>
          </div>
        </header>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {activeTab === 'search-articles' && <SearchArticles />}
          {activeTab === 'journal-rankings' && <JournalRankings />}
          {activeTab === 'mesh-terms' && <MeshTerms />}
          {activeTab === 'bookmarks' && <Bookmarks />}
          {activeTab === 'settings' && <Settings />}
        </main>

        <footer className="bg-white border-t">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <p className="text-center text-gray-500">© 2025 Medical Literature Finder</p>
          </div>
        </footer>
      </div>
    </QueryClientProvider>
  )
}

export default App