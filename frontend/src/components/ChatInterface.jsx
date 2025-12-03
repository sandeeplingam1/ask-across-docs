import React, { useState, useEffect, useRef } from 'react';
import { Send, Loader2, FileText, AlertCircle, Sparkles } from 'lucide-react';
import api from '../api';

export default function ChatInterface({ engagementId }) {
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [loadingHistory, setLoadingHistory] = useState(true);
    const [error, setError] = useState(null);
    const [showTemplateSelector, setShowTemplateSelector] = useState(false);
    const [templates, setTemplates] = useState([]);
    const [loadingTemplates, setLoadingTemplates] = useState(false);
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
    }, [engagementId]);

    const loadHistory = async () => {
        try {
            setLoadingHistory(true);
            setError(null);
            const history = await api.getQuestionHistory(engagementId);
            
            // Convert history to chat messages format
            const chatMessages = history
                .filter(item => item.confidence !== 'pending') // Exclude pending questions
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
            inputRef.current?.focus();
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

                                        {/* Answer Text */}
                                        <p className="text-gray-900 whitespace-pre-wrap leading-relaxed">
                                            {msg.text}
                                        </p>

                                        {/* Sources */}
                                        {msg.sources && msg.sources.length > 0 && (
                                            <div className="pt-3 border-t border-gray-200">
                                                <p className="text-xs font-medium text-gray-600 mb-2">
                                                    📄 Sources:
                                                </p>
                                                <div className="space-y-1">
                                                    {msg.sources.slice(0, 3).map((source, i) => (
                                                        <div key={i} className="text-xs text-gray-600">
                                                            • {source.filename} {source.page && `(Page ${source.page})`}
                                                        </div>
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
