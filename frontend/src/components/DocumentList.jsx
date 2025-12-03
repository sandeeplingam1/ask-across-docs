import React, { useState, useEffect } from 'react';
import { documentApi } from '../api';
import { FileText, Trash2, CheckCircle, XCircle, Clock } from 'lucide-react';

export default function DocumentList({ engagement, refreshTrigger }) {
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedDocs, setSelectedDocs] = useState(new Set());
    const [deleting, setDeleting] = useState(false);
    const [processing, setProcessing] = useState(false);

    useEffect(() => {
        loadDocuments();
    }, [engagement.id, refreshTrigger]);

    // Auto-refresh when there are processing or queued documents
    useEffect(() => {
        const hasProcessingDocs = documents.some(d => 
            d.status === 'queued' || d.status === 'processing'
        );

        if (hasProcessingDocs) {
            const intervalId = setInterval(() => {
                loadDocuments();
            }, 3000); // Check every 3 seconds

            return () => clearInterval(intervalId);
        }
    }, [documents, engagement.id]);

    const loadDocuments = async () => {
        try {
            const response = await documentApi.list(engagement.id);
            setDocuments(response.data);
            setSelectedDocs(new Set()); // Clear selection when reloading
        } catch (error) {
            console.error('Failed to load documents:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleProcessQueued = async () => {
        const queuedCount = documents.filter(d => d.status === 'queued').length;
        if (queuedCount === 0) {
            alert('No queued documents to process');
            return;
        }

        if (!confirm(`Process ${queuedCount} queued document(s)?`)) return;

        setProcessing(true);
        try {
            const response = await documentApi.processQueued(engagement.id);
            alert(`Processed: ${response.data.processed}, Failed: ${response.data.failed}`);
            loadDocuments();
        } catch (error) {
            console.error('Failed to process documents:', error);
            alert('Error processing documents: ' + (error.response?.data?.detail || error.message));
        } finally {
            setProcessing(false);
        }
    };

    const toggleSelection = (docId) => {
        const newSelection = new Set(selectedDocs);
        if (newSelection.has(docId)) {
            newSelection.delete(docId);
        } else {
            newSelection.add(docId);
        }
        setSelectedDocs(newSelection);
    };

    const toggleSelectAll = () => {
        if (selectedDocs.size === documents.length) {
            setSelectedDocs(new Set());
        } else {
            setSelectedDocs(new Set(documents.map(d => d.id)));
        }
    };

    const handleBulkDelete = async () => {
        if (selectedDocs.size === 0) return;
        
        if (!confirm(`Delete ${selectedDocs.size} selected document(s)?`)) return;

        setDeleting(true);
        const deletePromises = Array.from(selectedDocs).map(docId =>
            documentApi.delete(engagement.id, docId).catch(err => {
                console.error(`Failed to delete ${docId}:`, err);
                return { error: true, docId };
            })
        );

        try {
            const results = await Promise.all(deletePromises);
            const failed = results.filter(r => r?.error).length;
            
            if (failed > 0) {
                alert(`Deleted ${selectedDocs.size - failed} documents. ${failed} failed.`);
            }
            
            loadDocuments();
        } catch (error) {
            console.error('Bulk delete failed:', error);
            alert('Error deleting documents');
        } finally {
            setDeleting(false);
        }
    };

    const handleDelete = async (documentId, filename) => {
        if (!confirm(`Delete "${filename}"?`)) return;

        try {
            await documentApi.delete(engagement.id, documentId);
            loadDocuments();
        } catch (error) {
            console.error('Failed to delete document:', error);
            alert('Error deleting document');
        }
    };

    const formatFileSize = (bytes) => {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'completed':
                return <CheckCircle className="text-green-600" size={20} />;
            case 'failed':
                return <XCircle className="text-red-600" size={20} />;
            default:
                return <Clock className="text-yellow-600" size={20} />;
        }
    };

    if (loading) {
        return <div className="text-gray-500">Loading documents...</div>;
    }

    if (documents.length === 0) {
        return (
            <div className="card text-center py-8">
                <FileText size={48} className="mx-auto text-gray-400 mb-3" />
                <p className="text-gray-600">No documents uploaded yet</p>
            </div>
        );
    }

    return (
        <div className="card">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">
                    Documents ({documents.length})
                </h3>
                
                <div className="flex gap-2">
                    {selectedDocs.size > 0 && (
                        <button
                            onClick={handleBulkDelete}
                            disabled={deleting}
                            className="btn-secondary flex items-center gap-2 text-sm"
                        >
                            <Trash2 size={16} />
                            Delete {selectedDocs.size} selected
                        </button>
                    )}
                </div>
            </div>

            <div className="mb-3 pb-3 border-b flex items-center gap-2">
                <input
                    type="checkbox"
                    checked={selectedDocs.size === documents.length && documents.length > 0}
                    onChange={toggleSelectAll}
                    className="w-4 h-4 text-primary-600 rounded focus:ring-2 focus:ring-primary-500"
                />
                <span className="text-sm text-gray-600">
                    Select All {selectedDocs.size > 0 && `(${selectedDocs.size} selected)`}
                </span>
            </div>

            <div className="space-y-2">
                {documents.map((doc) => (
                    <div
                        key={doc.id}
                        className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                    >
                        <div className="flex items-center gap-3 flex-1 min-w-0">
                            <input
                                type="checkbox"
                                checked={selectedDocs.has(doc.id)}
                                onChange={() => toggleSelection(doc.id)}
                                className="w-4 h-4 text-primary-600 rounded focus:ring-2 focus:ring-primary-500 flex-shrink-0"
                            />
                            <FileText className="text-primary-600 flex-shrink-0" size={20} />

                            <div className="flex-1 min-w-0">
                                <p className="font-medium text-gray-900 truncate">
                                    {doc.filename}
                                </p>
                                <div className="flex gap-4 text-sm text-gray-600">
                                    <span>{formatFileSize(doc.file_size)}</span>
                                    {doc.status === 'completed' && (
                                        <span>{doc.chunk_count} chunks</span>
                                    )}
                                </div>
                            </div>

                            <div className="flex items-center gap-2">
                                {getStatusIcon(doc.status)}

                                <button
                                    onClick={() => handleDelete(doc.id, doc.filename)}
                                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                >
                                    <Trash2 size={18} />
                                </button>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
