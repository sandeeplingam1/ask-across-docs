import React, { useState } from 'react';
import EngagementList from './components/EngagementList';
import EngagementView from './pages/EngagementView';
import QuestionTemplates from './pages/QuestionTemplates';
import { FileSearch, Library } from 'lucide-react';
import './index.css';

function App() {
    const [selectedEngagement, setSelectedEngagement] = useState(null);
    const [currentView, setCurrentView] = useState('engagements'); // 'engagements' or 'templates'

    const handleViewChange = (view) => {
        setCurrentView(view);
        setSelectedEngagement(null);
    };

    return (
        <div className="h-screen flex flex-col bg-gradient-to-br from-gray-50 via-blue-50 to-gray-100">
            {/* Header - Glass Morphism */}
            <header className="bg-white/80 backdrop-blur-md border-b border-gray-200/50 shadow-sm sticky top-0 z-10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
                    <div className="flex items-center justify-between">
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
                        
                        {/* Navigation */}
                        <nav className="flex gap-2">
                            <button
                                onClick={() => handleViewChange('engagements')}
                                className={`flex items-center gap-2 px-4 py-2 rounded-md font-medium transition-colors ${
                                    currentView === 'engagements'
                                        ? 'bg-blue-600 text-white'
                                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                }`}
                            >
                                <FileSearch size={18} />
                                Engagements
                            </button>
                            <button
                                onClick={() => handleViewChange('templates')}
                                className={`flex items-center gap-2 px-4 py-2 rounded-md font-medium transition-colors ${
                                    currentView === 'templates'
                                        ? 'bg-blue-600 text-white'
                                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                }`}
                            >
                                <Library size={18} />
                                Templates
                            </button>
                        </nav>
                    </div>
                </div>
            </header>

            {/* Main Content - Full Width, Fixed Height */}
            <main className="flex-1 overflow-hidden py-4">
                {currentView === 'templates' ? (
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <QuestionTemplates />
                    </div>
                ) : selectedEngagement ? (
                    <EngagementView
                        engagement={selectedEngagement}
                        onBack={() => setSelectedEngagement(null)}
                    />
                ) : (
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <EngagementList onSelectEngagement={setSelectedEngagement} />
                    </div>
                )}
            </main>
        </div>
    );
}

export default App;
