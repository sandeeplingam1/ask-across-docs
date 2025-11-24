import React, { useState, useEffect } from 'react';
import { engagementApi } from '../api';
import { FolderPlus, Folder, Trash2, ChevronRight } from 'lucide-react';

export default function EngagementList({ onSelectEngagement }) {
    const [engagements, setEngagements] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        client_name: '',
    });

    useEffect(() => {
        loadEngagements();
    }, []);

    const loadEngagements = async () => {
        try {
            const response = await engagementApi.list();
            setEngagements(response.data);
        } catch (error) {
            console.error('Failed to load engagements:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = async (e) => {
        e.preventDefault();
        try {
            await engagementApi.create(formData);
            setFormData({ name: '', description: '', client_name: '' });
            setShowCreateForm(false);
            loadEngagements();
        } catch (error) {
            console.error('Failed to create engagement:', error);
            alert('Error creating engagement');
        }
    };

    const handleDelete = async (id, name) => {
        if (!confirm(`Delete engagement "${name}"? This will delete all documents and Q&A history.`)) {
            return;
        }

        try {
            await engagementApi.delete(id);
            loadEngagements();
        } catch (error) {
            console.error('Failed to delete engagement:', error);
            alert('Error deleting engagement');
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-gray-500">Loading engagements...</div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-gray-900">Engagements</h2>
                <button
                    onClick={() => setShowCreateForm(!showCreateForm)}
                    className="btn-primary flex items-center gap-2"
                >
                    <FolderPlus size={20} />
                    New Engagement
                </button>
            </div>

            {showCreateForm && (
                <div className="card">
                    <h3 className="text-lg font-semibold mb-4">Create New Engagement</h3>
                    <form onSubmit={handleCreate} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Engagement Name *
                            </label>
                            <input
                                type="text"
                                required
                                value={formData.name}
                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                className="input"
                                placeholder="e.g., Client ABC - Q4 2024 Audit"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Client Name
                            </label>
                            <input
                                type="text"
                                value={formData.client_name}
                                onChange={(e) => setFormData({ ...formData, client_name: e.target.value })}
                                className="input"
                                placeholder="e.g., ABC Corporation"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Description
                            </label>
                            <textarea
                                value={formData.description}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                className="input"
                                rows="3"
                                placeholder="Optional description..."
                            />
                        </div>

                        <div className="flex gap-3">
                            <button type="submit" className="btn-primary">
                                Create Engagement
                            </button>
                            <button
                                type="button"
                                onClick={() => setShowCreateForm(false)}
                                className="btn-secondary"
                            >
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {engagements.length === 0 ? (
                <div className="card text-center py-12">
                    <Folder size={48} className="mx-auto text-gray-400 mb-4" />
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                        No Engagements Yet
                    </h3>
                    <p className="text-gray-600 mb-4">
                        Create your first engagement to start uploading documents
                    </p>
                </div>
            ) : (
                <div className="grid gap-4">
                    {engagements.map((engagement) => (
                        <div
                            key={engagement.id}
                            className="card hover:shadow-md transition-shadow cursor-pointer group"
                        >
                            <div className="flex items-center justify-between">
                                <div
                                    className="flex-1"
                                    onClick={() => onSelectEngagement(engagement)}
                                >
                                    <div className="flex items-center gap-3">
                                        <Folder className="text-primary-600" size={24} />
                                        <div>
                                            <h3 className="font-semibold text-lg text-gray-900">
                                                {engagement.name}
                                            </h3>
                                            {engagement.client_name && (
                                                <p className="text-sm text-gray-600">
                                                    Client: {engagement.client_name}
                                                </p>
                                            )}
                                            {engagement.description && (
                                                <p className="text-sm text-gray-500 mt-1">
                                                    {engagement.description}
                                                </p>
                                            )}
                                            <p className="text-sm text-gray-500 mt-2">
                                                {engagement.document_count} document{engagement.document_count !== 1 ? 's' : ''}
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleDelete(engagement.id, engagement.name);
                                        }}
                                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                    >
                                        <Trash2 size={20} />
                                    </button>
                                    <button
                                        onClick={() => onSelectEngagement(engagement)}
                                        className="p-2 text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                                    >
                                        <ChevronRight size={20} />
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
