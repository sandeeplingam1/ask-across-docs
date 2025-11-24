import React, { useState } from 'react';
import EngagementList from './components/EngagementList';
import EngagementView from './pages/EngagementView';
import { FileSearch } from 'lucide-react';
import './index.css';

function App() {
    const [selectedEngagement, setSelectedEngagement] = useState(null);

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Header */}
            <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
                    <div className="flex items-center gap-3">
                        <FileSearch className="text-primary-600" size={32} />
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900">
                                Audit App
                            </h1>
                            <p className="text-sm text-gray-600">
                                Document Q&A for Audit Engagements
                            </p>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {selectedEngagement ? (
                    <EngagementView
                        engagement={selectedEngagement}
                        onBack={() => setSelectedEngagement(null)}
                    />
                ) : (
                    <EngagementList onSelectEngagement={setSelectedEngagement} />
                )}
            </main>

            {/* Footer */}
            <footer className="mt-16 border-t border-gray-200 bg-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                    <p className="text-center text-sm text-gray-500">
                        Powered by Azure OpenAI • ChromaDB / Azure AI Search
                    </p>
                </div>
            </footer>
        </div>
    );
}

export default App;
