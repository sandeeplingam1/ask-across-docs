import React, { useState } from 'react';
import { MessageSquare, FileText, AlertTriangle, CheckCircle2, ExternalLink } from 'lucide-react';
import DocumentViewer from './DocumentViewer';

export default function AnswerDisplay({ answer }) {
    const [viewingDocument, setViewingDocument] = useState(null);

    // Handle both single answer and batch answers
    const answers = answer.answers || [answer];

    const getConfidenceBadge = (confidence) => {
        const colors = {
            high: 'bg-green-100 text-green-800',
            medium: 'bg-yellow-100 text-yellow-800',
            low: 'bg-red-100 text-red-800',
        };

        const icons = {
            high: <CheckCircle2 size={14} />,
            medium: <AlertTriangle size={14} />,
            low: <AlertTriangle size={14} />,
        };

        return (
            <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${colors[confidence] || colors.low}`}>
                {icons[confidence]}
                {confidence} confidence
            </span>
        );
    };

    const handleViewDocument = (source) => {
        setViewingDocument(source);
    };

    return (
        <>
            <div className="space-y-4">
                {answers.map((ans, index) => (
                    <div key={index} className="card">
                        <div className="flex items-start gap-3 mb-4">
                            <MessageSquare className="text-primary-600 flex-shrink-0 mt-1" size={24} />
                            <div className="flex-1">
                                <h3 className="font-semibold text-lg text-gray-900 mb-2">
                                    {ans.question}
                                </h3>
                                {getConfidenceBadge(ans.confidence)}
                            </div>
                        </div>

                        <div className="bg-gray-50 rounded-lg p-4 mb-4">
                            <p className="text-gray-900 whitespace-pre-wrap leading-relaxed">
                                {ans.answer}
                            </p>
                        </div>

                        {ans.sources && ans.sources.length > 0 && (
                            <div>
                                <h4 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
                                    <FileText size={18} />
                                    Sources ({ans.sources.length}) - Click to view document
                                </h4>
                                <div className="space-y-2">
                                    {ans.sources.map((source, idx) => (
                                        <div
                                            key={idx}
                                            className="bg-white border border-gray-200 rounded-lg p-3 hover:border-primary-400 hover:shadow-md transition-all cursor-pointer"
                                            onClick={() => handleViewDocument(source)}
                                        >
                                            <div className="flex items-center justify-between mb-2">
                                                <div className="flex items-center gap-2">
                                                    <span className="text-sm font-medium text-gray-700">
                                                        Source {idx + 1}
                                                    </span>
                                                    {source.document_name && (
                                                        <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                                                            {source.document_name}
                                                        </span>
                                                    )}
                                                    {source.page_number && (
                                                        <span className="text-sm font-medium text-primary-600 flex items-center gap-1">
                                                            <ExternalLink size={14} />
                                                            Page {source.page_number}
                                                        </span>
                                                    )}
                                                </div>
                                                <span className="text-xs text-gray-500">
                                                    Similarity: {(source.similarity_score * 100).toFixed(1)}%
                                                </span>
                                            </div>
                                            <p className="text-sm text-gray-600 line-clamp-3">
                                                {source.chunk_text}
                                            </p>
                                            <p className="text-xs text-primary-600 mt-2 flex items-center gap-1">
                                                <ExternalLink size={12} />
                                                Click to view in document
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {/* Document Viewer Modal */}
            {viewingDocument && (
                <DocumentViewer
                    documentId={viewingDocument.document_id}
                    filename={viewingDocument.document_name || 'Document'}
                    pageNumber={viewingDocument.page_number}
                    searchText={viewingDocument.chunk_text.substring(0, 50)} // First 50 chars for highlighting
                    onClose={() => setViewingDocument(null)}
                />
            )}
        </>
    );
}
