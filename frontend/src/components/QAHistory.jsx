import React, { useState, useEffect } from 'react';
import { questionApi } from '../api';
import { MessageSquare, ChevronDown, ChevronUp, Clock, FileText } from 'lucide-react';

export default function QAHistory({ engagement, onViewAnswer }) {
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [expandedId, setExpandedId] = useState(null);

    useEffect(() => {
        if (engagement) {
            loadHistory();
        }
    }, [engagement?.id]);

    const loadHistory = async () => {
        try {
            setLoading(true);
            const response = await questionApi.getHistory(engagement.id);
            setHistory(response.data);
        } catch (error) {
            console.error('Failed to load Q&A history:', error);
        } finally {
            setLoading(false);
        }
    };

    const toggleExpand = (id) => {
        setExpandedId(expandedId === id ? null : id);
    };

    const formatDate = (dateString) => {
        const date = new Date(dateString);
        return new Intl.DateTimeFormat('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(date);
    };

    const getConfidenceBadge = (confidence) => {
        const colors = {
            high: 'bg-green-100 text-green-800',
            medium: 'bg-yellow-100 text-yellow-800',
            low: 'bg-red-100 text-red-800',
        };

        return (
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[confidence] || colors.low}`}>
                {confidence}
            </span>
        );
    };

    if (loading) {
        return (
            <div className="card">
                <div className="text-center py-8 text-gray-500">Loading history...</div>
            </div>
        );
    }

    if (history.length === 0) {
        return (
            <div className="card text-center py-8">
                <MessageSquare size={48} className="mx-auto text-gray-400 mb-3" />
                <p className="text-gray-600">No questions asked yet</p>
            </div>
        );
    }

    return (
        <div className="card">
            <h3 className="text-lg font-semibold mb-4">Q&A History ({history.length})</h3>

            <div className="space-y-3 max-h-[600px] overflow-y-auto">
                {history.map((item, index) => (
                    <div
                        key={index}
                        className="border border-gray-200 rounded-lg overflow-hidden hover:shadow-md transition-shadow"
                    >
                        {/* Question Header */}
                        <button
                            onClick={() => toggleExpand(index)}
                            className="w-full p-4 bg-gray-50 hover:bg-gray-100 transition-colors text-left flex items-start justify-between"
                        >
                            <div className="flex-1 min-w-0 mr-4">
                                <p className="font-medium text-gray-900 line-clamp-2">
                                    {item.question}
                                </p>
                                <div className="flex items-center gap-3 mt-2 text-sm text-gray-500">
                                    <span className="flex items-center gap-1">
                                        <Clock size={14} />
                                        {formatDate(item.answered_at)}
                                    </span>
                                    {getConfidenceBadge(item.confidence)}
                                    {item.sources && item.sources.length > 0 && (
                                        <span className="flex items-center gap-1">
                                            <FileText size={14} />
                                            {item.sources.length} sources
                                        </span>
                                    )}
                                </div>
                            </div>

                            {expandedId === index ? (
                                <ChevronUp size={20} className="text-gray-400 flex-shrink-0" />
                            ) : (
                                <ChevronDown size={20} className="text-gray-400 flex-shrink-0" />
                            )}
                        </button>

                        {/* Answer Content */}
                        {expandedId === index && (
                            <div className="p-4 bg-white border-t border-gray-200">
                                <div className="prose max-w-none">
                                    <p className="text-gray-900 whitespace-pre-wrap">
                                        {item.answer}
                                    </p>
                                </div>

                                {item.sources && item.sources.length > 0 && (
                                    <div className="mt-4 pt-4 border-t border-gray-200">
                                        <h4 className="text-sm font-semibold text-gray-900 mb-2">
                                            Sources ({item.sources.length})
                                        </h4>
                                        <div className="space-y-2">
                                            {item.sources.map((source, idx) => (
                                                <div
                                                    key={idx}
                                                    className="text-sm bg-gray-50 p-3 rounded-lg"
                                                >
                                                    <div className="flex items-center justify-between mb-1">
                                                        <span className="font-medium text-gray-700">
                                                            Source {idx + 1}
                                                            {source.page_number && (
                                                                <span className="text-primary-600 ml-2">
                                                                    (Page {source.page_number})
                                                                </span>
                                                            )}
                                                        </span>
                                                        <span className="text-xs text-gray-500">
                                                            {(source.similarity_score * 100).toFixed(1)}% match
                                                        </span>
                                                    </div>
                                                    <p className="text-gray-600 line-clamp-2">
                                                        {source.chunk_text}
                                                    </p>
                                                    {onViewAnswer && (
                                                        <button
                                                            onClick={() => onViewAnswer(item)}
                                                            className="text-primary-600 text-xs mt-2 hover:underline"
                                                        >
                                                            View full answer
                                                        </button>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}
