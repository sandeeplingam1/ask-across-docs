import React, { useState } from 'react';
import { ArrowLeft, Upload as UploadIcon, MessageSquare } from 'lucide-react';
import DocumentUpload from '../components/DocumentUpload';
import DocumentList from '../components/DocumentList';
import ChatInterface from '../components/ChatInterface';
import QuestionTemplateList from '../components/QuestionTemplateList';
import DocumentViewer from '../components/DocumentViewer';
import api from '../api';

export default function EngagementView({ engagement, onBack }) {
    const [activeTab, setActiveTab] = useState('documents');
    const [refreshDocuments, setRefreshDocuments] = useState(0);
    const [showTemplateSelector, setShowTemplateSelector] = useState(false);
    const [applyingTemplate, setApplyingTemplate] = useState(false);
    const [viewingDocument, setViewingDocument] = useState(null);

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

    const handleViewDocument = (docInfo) => {
        setViewingDocument(docInfo);
    };

    return (
        <div className="h-full flex flex-col overflow-hidden">
            {/* Header - Compact with horizontal padding - Glass Effect */}
            <div className="flex items-center justify-between py-2 px-4 sm:px-6 bg-white/60 backdrop-blur-sm rounded-t-2xl">
                <div className="flex items-center gap-3">
                    <button
                        onClick={onBack}
                        className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        <ArrowLeft size={20} />
                    </button>
                    <div>
                        <h1 className="text-xl font-bold text-gray-900">
                            {engagement.name}
                        </h1>
                        {engagement.client_name && (
                            <p className="text-xs text-gray-500">Client: {engagement.client_name}</p>
                        )}
                    </div>
                </div>
            </div>

            {/* Tabs - Compact with horizontal padding - Glass Effect */}
            <div className="border-b border-gray-200/50 px-4 sm:px-6 bg-white/40 backdrop-blur-sm">
                <nav className="flex gap-6">
                    <button
                        onClick={() => setActiveTab('documents')}
                        className={`
              pb-2 px-1 border-b-2 font-medium text-sm transition-all
              ${activeTab === 'documents'
                                ? 'border-blue-600 text-blue-700 bg-blue-50/50 rounded-t-lg'
                                : 'border-transparent text-gray-600 hover:text-gray-800 hover:bg-white/30'
                            }
            `}
                    >
                        <div className="flex items-center gap-2">
                            <UploadIcon size={18} />
                            Documents
                        </div>
                    </button>

                    <button
                        onClick={() => setActiveTab('chat')}
                        className={`
              pb-2 px-1 border-b-2 font-medium text-sm transition-all
              ${activeTab === 'chat'
                                ? 'border-blue-600 text-blue-700 bg-blue-50/50 rounded-t-lg'
                                : 'border-transparent text-gray-600 hover:text-gray-800 hover:bg-white/30'
                            }
            `}
                    >
                        <div className="flex items-center gap-2">
                            <MessageSquare size={18} />
                            Chat
                        </div>
                    </button>
                </nav>
            </div>

            {/* Content - Full height with glass background */}
            <div className="flex-1 overflow-hidden bg-white/30 backdrop-blur-sm rounded-b-2xl shadow-lg">
                {activeTab === 'documents' && (
                    <div className="h-full px-4 sm:px-6 py-4 space-y-6 overflow-y-auto">
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
                    <div className="h-full">
                        <ChatInterface 
                            engagementId={engagement.id}
                            onViewDocument={handleViewDocument}
                        />
                    </div>
                )}
            </div>

            {/* Document Viewer Modal */}
            {viewingDocument && (
                <DocumentViewer
                    documentId={viewingDocument.documentId}
                    filename={viewingDocument.filename}
                    pageNumber={viewingDocument.pageNumber}
                    searchText={viewingDocument.searchText}
                    onClose={() => setViewingDocument(null)}
                />
            )}
        </div>
    );
}
