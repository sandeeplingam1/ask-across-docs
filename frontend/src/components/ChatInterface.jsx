import React, { useState, useEffect, useRef } from 'react';
import { Send, Loader2, FileText, AlertCircle, Sparkles, Trash2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import api from '../api';

export default function ChatInterface({ engagementId, onViewDocument }) {
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [loadingHistory, setLoadingHistory] = useState(true);
    const [error, setError] = useState(null);
    const [showTemplateSelector, setShowTemplateSelector] = useState(false);
    const [templates, setTemplates] = useState([]);
    const [loadingTemplates, setLoadingTemplates] = useState(false);
    const [lastMessageCount, setLastMessageCount] = useState(0);
    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    useEffect(() => {
        if (engagementId) {
            loadHistory();
        }
        // Focus input when component mounts
        setTimeout(() => inputRef.current?.focus(), 300);
    }, [engagementId]);

    // Auto-refresh history periodically to pick up new answers (but not while loading)
    useEffect(() => {
        if (!engagementId || isLoading) return;

        const intervalId = setInterval(() => {
            // Silently refresh in background
            api.getQuestionHistory(engagementId).then(history => {
                const chatMessages = history
                    .filter(item => item.confidence !== 'pending')
                    .sort((a, b) => new Date(a.answered_at) - new Date(b.answered_at)) // Sort oldest first
                    .map(item => ([
                        {
                            type: 'question',
                            text: item.question,
                            timestamp: item.answered_at
                        },
                        {
                            type: 'answer',
                            text: item.answer,
                            confidence: item.confidence,
                            sources: item.sources,
                            timestamp: item.answered_at
                        }
                    ]))
                    .flat();

                // Only update if message count changed (new messages arrived)
                if (chatMessages.length !== lastMessageCount) {
                    setMessages(chatMessages);
                    setLastMessageCount(chatMessages.length);
                }
            }).catch(err => {
                console.error('Background refresh failed:', err);
            });
        }, 10000); // Refresh every 10 seconds

        return () => clearInterval(intervalId);
    }, [engagementId, isLoading, lastMessageCount]);

    const loadHistory = async () => {
        try {
            setLoadingHistory(true);
            setError(null);
            const history = await api.getQuestionHistory(engagementId);
            
            // Convert history to chat messages format, sorted by timestamp (oldest first)
            const chatMessages = history
                .filter(item => item.confidence !== 'pending') // Exclude pending questions
                .sort((a, b) => new Date(a.answered_at) - new Date(b.answered_at)) // Sort oldest first
                .map(item => ([
                    {
                        type: 'question',
                        text: item.question,
                        timestamp: item.answered_at
                    },
                    {
                        type: 'answer',
                        text: item.answer,
                        confidence: item.confidence,
                        sources: item.sources,
                        timestamp: item.answered_at
                    }
                ]))
                .flat();

            setMessages(chatMessages);
            setLastMessageCount(chatMessages.length);
        } catch (error) {
            console.error('Failed to load history:', error);
            setError('Failed to load chat history. Please refresh the page.');
        } finally {
            setLoadingHistory(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!inputValue.trim() || isLoading) return;

        const question = inputValue.trim();
        setInputValue('');
        setIsLoading(true);

        // Add user question immediately
        setMessages(prev => [...prev, {
            type: 'question',
            text: question,
            timestamp: new Date().toISOString()
        }]);

        try {
            const answer = await api.askQuestion(engagementId, question);
            
            // Add answer
            setMessages(prev => [...prev, {
                type: 'answer',
                text: answer.answer,
                confidence: answer.confidence,
                sources: answer.sources,
                timestamp: new Date().toISOString()
            }]);
        } catch (error) {
            console.error('Failed to get answer:', error);
            setMessages(prev => [...prev, {
                type: 'error',
                text: 'Sorry, I encountered an error while processing your question. Please try again.',
                timestamp: new Date().toISOString()
            }]);
        } finally {
            setIsLoading(false);
            // Focus input after response
            setTimeout(() => inputRef.current?.focus(), 100);
        }
    };

    const loadTemplates = async () => {
        try {
            setLoadingTemplates(true);
            const data = await api.listQuestionTemplates();
            setTemplates(data);
        } catch (error) {
            console.error('Failed to load templates:', error);
        } finally {
            setLoadingTemplates(false);
        }
    };

    const handleApplyTemplate = async (template) => {
        if (!confirm(`Apply template "${template.name}" with ${template.question_count} questions?\n\nAnswers will be generated in the background.`)) {
            return;
        }

        try {
            const result = await api.applyTemplateToEngagement(template.id, engagementId);
            setShowTemplateSelector(false);
            alert(result.message + '\n\nAnswers are being generated. They will not appear in this chat.');
        } catch (error) {
            console.error('Failed to apply template:', error);
            alert('Failed to apply template. Please try again.');
        }
    };

    const handleClearHistory = async () => {
        if (!confirm('Clear all conversation history? This will delete all Q&A pairs for this engagement. This action cannot be undone.')) {
            return;
        }

        try {
            const result = await api.clearQuestionHistory(engagementId);
            setMessages([]);
            setLastMessageCount(0);
            alert(result.message || 'Conversation history cleared!');
        } catch (error) {
            console.error('Failed to clear history:', error);
            alert('Failed to clear history. Please try again.');
        }
    };

    const getConfidenceColor = (confidence) => {
        switch (confidence) {
            case 'high': return 'text-green-600 bg-green-50';
            case 'medium': return 'text-yellow-600 bg-yellow-50';
            case 'low': return 'text-red-600 bg-red-50';
            default: return 'text-gray-600 bg-gray-50';
        }
    };

    if (loadingHistory) {
        return (
            <div className="flex items-center justify-center h-96">
                <Loader2 className="animate-spin text-primary-600" size={32} />
                <span className="ml-2 text-gray-600">Loading conversation...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex items-center justify-center h-96">
                <div className="text-center">
                    <AlertCircle className="mx-auto text-red-500 mb-4" size={48} />
                    <p className="text-red-600">{error}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-[calc(100vh-20rem)] bg-white rounded-lg shadow-sm border border-gray-200">
            {/* Chat Header with Clear Button */}
            {messages.length > 0 && (
                <div className="border-b border-gray-200 px-4 py-3 bg-gray-50 flex justify-between items-center">
                    <span className="text-sm text-gray-600">
                        {messages.filter(m => m.type === 'question').length} questions in history
                    </span>
                    <button
                        onClick={handleClearHistory}
                        className="text-sm text-red-600 hover:text-red-700 flex items-center gap-1 hover:bg-red-50 px-3 py-1 rounded transition-colors"
                        title="Clear conversation history"
                    >
                        <Trash2 size={16} />
                        Clear History
                    </button>
                </div>
            )}
            
            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6" style={{ scrollbarWidth: 'thin' }}>
                {messages.length === 0 ? (
                    <div className="text-center py-12">
                        <FileText size={48} className="mx-auto text-gray-300 mb-4" />
                        <h3 className="text-lg font-medium text-gray-900 mb-2">
                            Start a conversation
                        </h3>
                        <p className="text-gray-600">
                            Ask questions about your documents
                        </p>
                    </div>
                ) : (
                    messages.map((msg, idx) => (
                        <div key={idx} className={`flex ${msg.type === 'question' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`max-w-3xl ${msg.type === 'question' ? 'w-auto' : 'w-full'}`}>
                                {msg.type === 'question' && (
                                    <div className="bg-primary-600 text-white rounded-2xl rounded-tr-sm px-4 py-3">
                                        <p className="whitespace-pre-wrap">{msg.text}</p>
                                    </div>
                                )}

                                {msg.type === 'answer' && (
                                    <div className="bg-gray-50 rounded-2xl rounded-tl-sm px-4 py-3 space-y-3">
                                        {/* Confidence Badge */}
                                        {msg.confidence && (
                                            <div className="flex items-center gap-2">
                                                <span className={`text-xs font-medium px-2 py-1 rounded-full ${getConfidenceColor(msg.confidence)}`}>
                                                    {msg.confidence.toUpperCase()} CONFIDENCE
                                                </span>
                                            </div>
                                        )}

                                        {/* Answer Text - Render as Markdown with styled citations */}
                                        <div className="text-gray-900 leading-relaxed prose prose-sm max-w-none">
                                            <ReactMarkdown
                                                remarkPlugins={[remarkGfm]}
                                                rehypePlugins={[rehypeRaw]}
                                                components={{
                                                    p: ({node, ...props}) => <p className="mb-2" {...props} />,
                                                    ul: ({node, ...props}) => <ul className="list-disc ml-4 mb-2 space-y-1" {...props} />,
                                                    ol: ({node, ...props}) => <ol className="list-decimal ml-4 mb-2 space-y-1" {...props} />,
                                                    li: ({node, ...props}) => <li className="ml-1" {...props} />,
                                                    strong: ({node, ...props}) => <strong className="font-semibold" {...props} />,
                                                    em: ({node, ...props}) => <em className="italic" {...props} />,
                                                }}
                                            >
                                                {(msg.text || '').replace(/\[(\d+)\]/g, '<sup class="text-blue-600 font-bold mx-0.5">[$1]</sup>')}
                                            </ReactMarkdown>
                                        </div>

                                        {/* Sources - Numbered Citations (ChatGPT Style) */}
                                        {msg.sources && msg.sources.length > 0 && (
                                            <div className="pt-3 border-t border-gray-200">
                                                <p className="text-xs font-medium text-gray-600 mb-2">
                                                    References:
                                                </p>
                                                <div className="space-y-2">
                                                    {msg.sources.slice(0, 3).map((source, i) => (
                                                        <button
                                                            key={i}
                                                            onClick={() => {
                                                                if (onViewDocument && source.document_id) {
                                                                    onViewDocument({
                                                                        documentId: source.document_id,
                                                                        filename: source.filename,
                                                                        pageNumber: source.page_number || 1,
                                                                        searchText: source.text?.substring(0, 100)
                                                                    });
                                                                }
                                                            }}
                                                            className="w-full text-left p-2 rounded-lg bg-blue-50 hover:bg-blue-100 transition-colors border border-blue-200"
                                                        >
                                                            <div className="flex items-start gap-2">
                                                                <span className="text-xs font-bold text-blue-700 bg-blue-200 px-1.5 py-0.5 rounded flex-shrink-0">
                                                                    [{i + 1}]
                                                                </span>
                                                                <div className="flex-1 min-w-0">
                                                                    <div className="text-xs font-medium text-blue-900">
                                                                        {source.filename || source.document_name || `Document ${source.document_id?.substring(0, 8)}` || 'Unknown Document'}
                                                                        {source.page_number && (
                                                                            <span className="text-blue-600 ml-1">
                                                                                - Page {source.page_number}
                                                                            </span>
                                                                        )}
                                                                    </div>
                                                                    {source.text && (
                                                                        <div className="text-xs text-gray-600 mt-1 line-clamp-2">
                                                                            {source.text.substring(0, 120)}...
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        </button>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {msg.type === 'error' && (
                                    <div className="bg-red-50 border border-red-200 rounded-2xl rounded-tl-sm px-4 py-3">
                                        <div className="flex items-start gap-2">
                                            <AlertCircle size={16} className="text-red-600 mt-0.5 flex-shrink-0" />
                                            <p className="text-red-800 text-sm">{msg.text}</p>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))
                )}

                {/* Loading Indicator */}
                {isLoading && (
                    <div className="flex justify-start">
                        <div className="bg-gray-50 rounded-2xl rounded-tl-sm px-4 py-3">
                            <div className="flex items-center gap-2 text-gray-600">
                                <Loader2 className="animate-spin" size={16} />
                                <span className="text-sm">Thinking...</span>
                            </div>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Template Selector */}
            {showTemplateSelector && (
                <div className="border-t border-gray-200 p-4 bg-blue-50 max-h-64 overflow-y-auto">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="font-semibold text-gray-900">Apply Question Template</h3>
                        <button
                            onClick={() => setShowTemplateSelector(false)}
                            className="text-gray-500 hover:text-gray-700"
                        >
                            ✕
                        </button>
                    </div>
                    {loadingTemplates ? (
                        <div className="flex items-center justify-center py-4">
                            <Loader2 className="animate-spin text-primary-600" size={24} />
                        </div>
                    ) : templates.length === 0 ? (
                        <p className="text-gray-600 text-sm">No templates available. Create one in the Templates tab.</p>
                    ) : (
                        <div className="space-y-2">
                            {templates.map((template) => (
                                <button
                                    key={template.id}
                                    onClick={() => handleApplyTemplate(template)}
                                    className="w-full text-left p-3 bg-white rounded-lg border border-gray-200 hover:border-primary-500 hover:bg-primary-50 transition-colors"
                                >
                                    <div className="font-medium text-gray-900">{template.name}</div>
                                    <div className="text-sm text-gray-600">
                                        {template.question_count} questions
                                        {template.description && ` • ${template.description}`}
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Input Area */}
            <div className="border-t border-gray-200 p-4 bg-white">
                <form onSubmit={handleSubmit} className="flex gap-2">
                    <button
                        type="button"
                        onClick={() => {
                            setShowTemplateSelector(!showTemplateSelector);
                            if (!showTemplateSelector && templates.length === 0) {
                                loadTemplates();
                            }
                        }}
                        className="px-4 py-3 bg-purple-100 text-purple-700 rounded-lg hover:bg-purple-200 transition-colors flex items-center gap-2"
                        title="Apply a question template"
                    >
                        <Sparkles size={20} />
                    </button>
                    <input
                        ref={inputRef}
                        type="text"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        placeholder="Ask a question about the documents..."
                        className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        disabled={isLoading}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                handleSubmit(e);
                            }
                        }}
                    />
                    <button
                        type="submit"
                        disabled={!inputValue.trim() || isLoading}
                        className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                        {isLoading ? (
                            <Loader2 className="animate-spin" size={20} />
                        ) : (
                            <Send size={20} />
                        )}
                    </button>
                </form>
            </div>
        </div>
    );
}
