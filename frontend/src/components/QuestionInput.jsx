import React, { useState, useRef } from 'react';
import { questionApi } from '../api';
import { Send, Upload, Loader, FileText, AlertCircle } from 'lucide-react';

export default function QuestionInput({ engagement, onAnswerReceived }) {
    const [question, setQuestion] = useState('');
    const [loading, setLoading] = useState(false);
    const [batchLoading, setBatchLoading] = useState(false);
    const fileInputRef = useRef(null);

    const handleAskQuestion = async (e) => {
        e.preventDefault();
        if (!question.trim() || loading) return;

        setLoading(true);
        try {
            const response = await questionApi.ask(engagement.id, question);
            onAnswerReceived(response.data);
            setQuestion('');
        } catch (error) {
            console.error('Failed to ask question:', error);
            alert('Error: ' + (error.response?.data?.detail || error.message));
        } finally {
            setLoading(false);
        }
    };

    const handleBatchUpload = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setBatchLoading(true);
        try {
            const response = await questionApi.batchAskFile(engagement.id, file);
            onAnswerReceived(response.data);

            // Reset file input
            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
        } catch (error) {
            console.error('Failed to process batch questions:', error);
            alert('Error: ' + (error.response?.data?.detail || error.message));
        } finally {
            setBatchLoading(false);
        }
    };

    return (
        <div className="card">
            <h3 className="text-lg font-semibold mb-4">Ask Questions</h3>

            <form onSubmit={handleAskQuestion} className="space-y-4">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Type your question
                    </label>
                    <div className="flex gap-2">
                        <input
                            type="text"
                            value={question}
                            onChange={(e) => setQuestion(e.target.value)}
                            placeholder="e.g., What are the key findings in the financial statements?"
                            className="input flex-1"
                            disabled={loading || batchLoading}
                        />
                        <button
                            type="submit"
                            disabled={loading || batchLoading || !question.trim()}
                            className="btn-primary flex items-center gap-2"
                        >
                            {loading ? (
                                <>
                                    <Loader className="animate-spin" size={20} />
                                    Thinking...
                                </>
                            ) : (
                                <>
                                    <Send size={20} />
                                    Ask
                                </>
                            )}
                        </button>
                    </div>
                </div>

                <div className="relative">
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                        <span className="h-px flex-1 bg-gray-300" />
                        <span>OR</span>
                        <span className="h-px flex-1 bg-gray-300" />
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Upload questions file
                    </label>
                    <div className="flex items-center gap-4">
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept=".txt,.doc,.docx"
                            onChange={handleBatchUpload}
                            disabled={loading || batchLoading}
                            className="hidden"
                            id="batch-upload"
                        />
                        <label
                            htmlFor="batch-upload"
                            className={`
                flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg cursor-pointer
                hover:bg-gray-50 transition-colors
                ${(loading || batchLoading) ? 'opacity-50 cursor-not-allowed' : ''}
              `}
                        >
                            {batchLoading ? (
                                <>
                                    <Loader className="animate-spin" size={20} />
                                    Processing...
                                </>
                            ) : (
                                <>
                                    <Upload size={20} />
                                    Choose File (.txt, .docx)
                                </>
                            )}
                        </label>
                        <span className="text-sm text-gray-500">
                            One question per line
                        </span>
                    </div>
                </div>
            </form>

            <div className="mt-4 p-3 bg-blue-50 rounded-lg flex gap-2">
                <AlertCircle className="text-blue-600 flex-shrink-0" size={20} />
                <p className="text-sm text-blue-800">
                    Questions will be answered based only on documents uploaded to this engagement.
                </p>
            </div>
        </div>
    );
}
