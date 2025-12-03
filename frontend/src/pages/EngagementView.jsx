import React, { useState } from 'react';
import { ArrowLeft, Upload as UploadIcon, MessageSquare } from 'lucide-react';
import DocumentUpload from '../components/DocumentUpload';
import DocumentList from '../components/DocumentList';
import ChatInterface from '../components/ChatInterface';
import QuestionTemplateList from '../components/QuestionTemplateList';
import api from '../api';

export default function EngagementView({ engagement, onBack }) {
    const [activeTab, setActiveTab] = useState('documents');
    const [refreshDocuments, setRefreshDocuments] = useState(0);
    const [showTemplateSelector, setShowTemplateSelector] = useState(false);
    const [applyingTemplate, setApplyingTemplate] = useState(false);

    const handleUploadComplete = () => {
        setRefreshDocuments(prev => prev + 1);
    };

    const handleAnswerReceived = (answer) => {
        // No longer needed - ChatInterface handles its own state
        setActiveTab('chat');
    };

    const handleApplyTemplate = async (template) => {
        if (!confirm(`Apply template "${template.name}" with ${template.question_count} questions to this engagement?`)) {
            return;
        }

        try {
            setApplyingTemplate(true);
            const result = await api.applyTemplateToEngagement(template.id, engagement.id);
            alert(result.message + '\n\nAnswers are being generated in the background.');
            setShowTemplateSelector(false);
            // Don't switch tabs - template questions process silently
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
                        onClick={() => setActiveTab('chat')}
                        className={`
              pb-3 px-1 border-b-2 font-medium transition-colors
              ${activeTab === 'chat'
                                ? 'border-primary-600 text-primary-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700'
                            }
            `}
                    >
                        <div className="flex items-center gap-2">
                            <MessageSquare size={20} />
                            Chat
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

                {activeTab === 'chat' && (
                    <ChatInterface engagementId={engagement.id} />
                )}
            </div>
        </div>
    );
}
