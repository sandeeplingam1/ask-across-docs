import React, { useState, useEffect } from 'react';
import { documentApi } from '../api';
import { FileText, Trash2, CheckCircle, XCircle, Clock } from 'lucide-react';

export default function DocumentList({ engagement, refreshTrigger }) {
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadDocuments();
    }, [engagement.id, refreshTrigger]);

    const loadDocuments = async () => {
        try {
            const response = await documentApi.list(engagement.id);
            setDocuments(response.data);
        } catch (error) {
            console.error('Failed to load documents:', error);
        } finally {
            setLoading(false);
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
            <h3 className="text-lg font-semibold mb-4">
                Documents ({documents.length})
            </h3>

            <div className="space-y-2">
                {documents.map((doc) => (
                    <div
                        key={doc.id}
                        className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                    >
                        <div className="flex items-center gap-3 flex-1 min-w-0">
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
