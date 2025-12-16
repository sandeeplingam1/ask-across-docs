import React, { useState } from 'react';
import { MessageSquare, FileText, AlertTriangle, CheckCircle2, ExternalLink } from 'lucide-react';
import DocumentViewer from './DocumentViewer';

export default function AnswerDisplay({ answer }) {
    const [viewingDocument, setViewingDocument] = useState(null);
    const [selectedSourceIndex, setSelectedSourceIndex] = useState(null);

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

    const handleViewDocument = (source, sourceIndex) => {
        // Validate source has required fields
        if (!source || !source.document_id) {
            console.error('Invalid source object:', source);
            alert('Cannot open document: Missing document information');
            return;
        }
        
        console.log('Opening document:', {
            documentId: source.document_id,
            documentName: source.document_name,
            pageNumber: source.page_number,
            chunkText: source.chunk_text?.substring(0, 50) + '...'
        });
        
        setViewingDocument(source);
        setSelectedSourceIndex(sourceIndex);
    };

    // Parse answer text and make citations clickable
    const renderAnswerWithCitations = (answerText, sources) => {
        if (!sources || sources.length === 0) {
            return answerText;
        }

        // Split text by citation pattern [1], [2], etc.
        const citationRegex = /\[(\d+)\]/g;
        const parts = [];
        let lastIndex = 0;
        let match;

        while ((match = citationRegex.exec(answerText)) !== null) {
            // Add text before citation
            if (match.index > lastIndex) {
                parts.push({
                    type: 'text',
                    content: answerText.substring(lastIndex, match.index)
                });
            }

            // Add citation as clickable link
            const citationNumber = parseInt(match[1]);
            const sourceIndex = citationNumber - 1;
            
            if (sourceIndex >= 0 && sourceIndex < sources.length) {
                parts.push({
                    type: 'citation',
                    number: citationNumber,
                    sourceIndex: sourceIndex,
                    source: sources[sourceIndex]
                });
            } else {
                // Invalid citation, render as text
                parts.push({
                    type: 'text',
                    content: match[0]
                });
            }

            lastIndex = match.index + match[0].length;
        }

        // Add remaining text
        if (lastIndex < answerText.length) {
            parts.push({
                type: 'text',
                content: answerText.substring(lastIndex)
            });
        }

        return parts.map((part, idx) => {
            if (part.type === 'text') {
                return <span key={idx}>{part.content}</span>;
            } else {
                return (
                    <button
                        key={idx}
                        onClick={(e) => {
                            e.stopPropagation();
                            handleViewDocument(part.source, part.sourceIndex);
                        }}
                        className="inline-flex items-center justify-center w-6 h-6 text-xs font-semibold text-white bg-primary-600 hover:bg-primary-700 rounded-full mx-0.5 cursor-pointer transition-all hover:scale-110 shadow-sm"
                        title={`View source: ${part.source.document_name || 'Document'}`}
                    >
                        {part.number}
                    </button>
                );
            }
        });
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
                            <div className="text-gray-900 whitespace-pre-wrap leading-relaxed">
                                {renderAnswerWithCitations(ans.answer, ans.sources)}
                            </div>
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
                                            className={`bg-white border rounded-lg p-3 hover:border-primary-400 hover:shadow-md transition-all cursor-pointer ${
                                                selectedSourceIndex === idx ? 'border-primary-500 ring-2 ring-primary-200' : 'border-gray-200'
                                            }`}
                                            onClick={() => handleViewDocument(source, idx)}
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
            {viewingDocument && viewingDocument.document_id && (
                <DocumentViewer
                    documentId={viewingDocument.document_id}
                    filename={viewingDocument.document_name || 'Document'}
                    pageNumber={viewingDocument.page_number}
                    searchText={viewingDocument.chunk_text || ''}
                    onClose={() => {
                        setViewingDocument(null);
                        setSelectedSourceIndex(null);
                    }}
                />
            )}
        </>
    );
}
