import React, { useState } from 'react';
import { ArrowLeft, Upload as UploadIcon, MessageSquare, History } from 'lucide-react';
import DocumentUpload from '../components/DocumentUpload';
import DocumentList from '../components/DocumentList';
import QuestionInput from '../components/QuestionInput';
import AnswerDisplay from '../components/AnswerDisplay';
import QAHistory from '../components/QAHistory';
import QuestionTemplateList from '../components/QuestionTemplateList';
import api from '../api';

export default function EngagementView({ engagement, onBack }) {
    const [activeTab, setActiveTab] = useState('documents');
    const [refreshDocuments, setRefreshDocuments] = useState(0);
    const [currentAnswer, setCurrentAnswer] = useState(null);
    const [showTemplateSelector, setShowTemplateSelector] = useState(false);
    const [applyingTemplate, setApplyingTemplate] = useState(false);

    const handleUploadComplete = () => {
        setRefreshDocuments(prev => prev + 1);
    };

    const handleAnswerReceived = (answer) => {
        setCurrentAnswer(answer);
        setActiveTab('qa');
    };

    const handleApplyTemplate = async (template) => {
        if (!confirm(`Apply template "${template.name}" with ${template.question_count} questions to this engagement?`)) {
            return;
        }

        try {
            setApplyingTemplate(true);
            const result = await api.applyTemplateToEngagement(template.id, engagement.id);
            alert(result.message);
            setShowTemplateSelector(false);
            setActiveTab('history'); // Switch to history to see the applied questions
        } catch (err) {
            console.error('Failed to apply template:', err);
            alert('Failed to apply template. Please try again.');
        } finally {
            setApplyingTemplate(false);
        }
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <button
                        onClick={onBack}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        <ArrowLeft size={24} />
                    </button>
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">
                            {engagement.name}
                        </h1>
                        {engagement.client_name && (
                            <p className="text-gray-600">Client: {engagement.client_name}</p>
                        )}
                    </div>
                </div>
                
                {/* Apply Template Button */}
                <button
                    onClick={() => setShowTemplateSelector(!showTemplateSelector)}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                    disabled={applyingTemplate}
                >
                    {showTemplateSelector ? 'Hide Templates' : 'Apply Template'}
                </button>
            </div>

            {/* Template Selector Modal */}
            {showTemplateSelector && (
                <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-4">
                    <h3 className="text-lg font-semibold text-blue-900 mb-3">
                        Select a template to apply
                    </h3>
                    <QuestionTemplateList onSelectTemplate={handleApplyTemplate} />
                </div>
            )}

            {/* Tabs */}
            <div className="border-b border-gray-200">
                <nav className="flex gap-8">
                    <button
                        onClick={() => setActiveTab('documents')}
                        className={`
              pb-3 px-1 border-b-2 font-medium transition-colors
              ${activeTab === 'documents'
                                ? 'border-primary-600 text-primary-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700'
                            }
            `}
                    >
                        <div className="flex items-center gap-2">
                            <UploadIcon size={20} />
                            Documents
                        </div>
                    </button>

                    <button
                        onClick={() => setActiveTab('qa')}
                        className={`
              pb-3 px-1 border-b-2 font-medium transition-colors
              ${activeTab === 'qa'
                                ? 'border-primary-600 text-primary-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700'
                            }
            `}
                    >
                        <div className="flex items-center gap-2">
                            <MessageSquare size={20} />
                            Q&A
                        </div>
                    </button>

                    <button
                        onClick={() => setActiveTab('history')}
                        className={`
              pb-3 px-1 border-b-2 font-medium transition-colors
              ${activeTab === 'history'
                                ? 'border-primary-600 text-primary-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700'
                            }
            `}
                    >
                        <div className="flex items-center gap-2">
                            <History size={20} />
                            History
                        </div>
                    </button>
                </nav>
            </div>

            {/* Content */}
            <div>
                {activeTab === 'documents' && (
                    <div className="space-y-6">
                        <DocumentUpload
                            engagement={engagement}
                            onUploadComplete={handleUploadComplete}
                        />
                        <DocumentList
                            engagement={engagement}
                            refreshTrigger={refreshDocuments}
                        />
                    </div>
                )}

                {activeTab === 'qa' && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <div>
                            <QuestionInput
                                engagement={engagement}
                                onAnswerReceived={handleAnswerReceived}
                            />
                        </div>
                        <div>
                            {currentAnswer ? (
                                <AnswerDisplay answer={currentAnswer} />
                            ) : (
                                <div className="card text-center py-12">
                                    <MessageSquare size={48} className="mx-auto text-gray-400 mb-3" />
                                    <p className="text-gray-600">
                                        Ask a question to see answers here
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {activeTab === 'history' && (
                    <QAHistory
                        engagement={engagement}
                        onViewAnswer={setCurrentAnswer}
                    />
                )}
            </div>
        </div>
    );
}
