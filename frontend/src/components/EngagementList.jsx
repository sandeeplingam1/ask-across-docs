import React, { useState, useEffect } from 'react';
import { engagementApi } from '../api';
import { FolderPlus, Folder, Trash2, ChevronRight, Edit2, Search, X, ArrowUpDown } from 'lucide-react';

export default function EngagementList({ onSelectEngagement }) {
    const [engagements, setEngagements] = useState([]);
    const [filteredEngagements, setFilteredEngagements] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [showEditForm, setShowEditForm] = useState(false);
    const [editingEngagement, setEditingEngagement] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [sortBy, setSortBy] = useState('created_at');
    const [sortOrder, setSortOrder] = useState('desc');
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        client_name: '',
    });

    useEffect(() => {
        loadEngagements();
    }, []);

    // Filter and sort engagements
    useEffect(() => {
        let filtered = [...engagements];
        
        // Search filter
        if (searchQuery.trim()) {
            const query = searchQuery.toLowerCase();
            filtered = filtered.filter(eng => 
                eng.name.toLowerCase().includes(query) ||
                (eng.client_name && eng.client_name.toLowerCase().includes(query)) ||
                (eng.description && eng.description.toLowerCase().includes(query))
            );
        }
        
        // Sort
        filtered.sort((a, b) => {
            let compareA, compareB;
            
            if (sortBy === 'name') {
                compareA = a.name.toLowerCase();
                compareB = b.name.toLowerCase();
            } else if (sortBy === 'client_name') {
                compareA = (a.client_name || '').toLowerCase();
                compareB = (b.client_name || '').toLowerCase();
            } else { // created_at
                compareA = new Date(a.created_at);
                compareB = new Date(b.created_at);
            }
            
            if (sortOrder === 'asc') {
                return compareA > compareB ? 1 : -1;
            } else {
                return compareA < compareB ? 1 : -1;
            }
        });
        
        setFilteredEngagements(filtered);
    }, [engagements, searchQuery, sortBy, sortOrder]);

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

    const handleEdit = async (e) => {
        e.preventDefault();
        try {
            await engagementApi.update(editingEngagement.id, formData);
            setFormData({ name: '', description: '', client_name: '' });
            setShowEditForm(false);
            setEditingEngagement(null);
            loadEngagements();
        } catch (error) {
            console.error('Failed to update engagement:', error);
            alert('Error updating engagement');
        }
    };

    const openEditForm = (engagement) => {
        setEditingEngagement(engagement);
        setFormData({
            name: engagement.name,
            description: engagement.description || '',
            client_name: engagement.client_name || '',
        });
        setShowEditForm(true);
        setShowCreateForm(false);
    };

    const handleDelete = async (id, name, documentCount) => {
        const confirmMessage = documentCount > 0
            ? `Delete engagement "${name}"?\n\nThis will permanently delete:\n• ${documentCount} document${documentCount !== 1 ? 's' : ''}\n• All Q&A history\n\nThis action cannot be undone.`
            : `Delete engagement "${name}"?\n\nThis action cannot be undone.`;

        if (!confirm(confirmMessage)) {
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

    const toggleSortOrder = () => {
        setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    };

    const clearSearch = () => {
        setSearchQuery('');
        document.getElementById('engagement-search')?.focus();
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-pulse space-y-4 w-full max-w-4xl">
                    <div className="h-24 bg-gray-200 rounded-lg"></div>
                    <div className="h-24 bg-gray-200 rounded-lg"></div>
                    <div className="h-24 bg-gray-200 rounded-lg"></div>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-gray-900">Engagements</h2>
                <button
                    onClick={() => {
                        setShowCreateForm(!showCreateForm);
                        setShowEditForm(false);
                    }}
                    className="btn-primary flex items-center gap-2"
                >
                    <FolderPlus size={20} />
                    New Engagement
                </button>
            </div>

            {/* Search and Sort Bar */}
            {engagements.length > 0 && (
                <div className="flex gap-3">
                    {/* Search */}
                    <div className="flex-1 relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
                        <input
                            id="engagement-search"
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Search engagements..."
                            className="input pl-10 pr-10"
                        />
                        {searchQuery && (
                            <button
                                onClick={clearSearch}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                            >
                                <X size={20} />
                            </button>
                        )}
                    </div>

                    {/* Sort */}
                    <div className="flex gap-2">
                        <select
                            value={sortBy}
                            onChange={(e) => setSortBy(e.target.value)}
                            className="input w-48"
                        >
                            <option value="created_at">Date Created</option>
                            <option value="name">Name</option>
                            <option value="client_name">Client Name</option>
                        </select>
                        <button
                            onClick={toggleSortOrder}
                            className="p-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                            title={sortOrder === 'asc' ? 'Ascending' : 'Descending'}
                        >
                            <ArrowUpDown 
                                size={20} 
                                className={`transform transition-transform ${sortOrder === 'desc' ? 'rotate-180' : ''}`}
                            />
                        </button>
                    </div>
                </div>
            )}

            {/* Create Form */}
            {showCreateForm && (
                <div className="card bg-white/80 backdrop-blur-sm border border-gray-200/50">
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
                                autoFocus
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
                                onClick={() => {
                                    setShowCreateForm(false);
                                    setFormData({ name: '', description: '', client_name: '' });
                                }}
                                className="btn-secondary"
                            >
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {/* Edit Form */}
            {showEditForm && (
                <div className="card bg-white/80 backdrop-blur-sm border border-blue-200/50">
                    <h3 className="text-lg font-semibold mb-4">Edit Engagement</h3>
                    <form onSubmit={handleEdit} className="space-y-4">
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
                                autoFocus
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
                            />
                        </div>

                        <div className="flex gap-3">
                            <button type="submit" className="btn-primary">
                                Save Changes
                            </button>
                            <button
                                type="button"
                                onClick={() => {
                                    setShowEditForm(false);
                                    setEditingEngagement(null);
                                    setFormData({ name: '', description: '', client_name: '' });
                                }}
                                className="btn-secondary"
                            >
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {/* Engagements List */}
            {engagements.length === 0 ? (
                <div className="card text-center py-12 bg-white/60 backdrop-blur-sm">
                    <Folder size={48} className="mx-auto text-gray-400 mb-4" />
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                        No Engagements Yet
                    </h3>
                    <p className="text-gray-600 mb-4">
                        Create your first engagement to start uploading documents and asking questions.
                    </p>
                    <button
                        onClick={() => setShowCreateForm(true)}
                        className="btn-primary inline-flex items-center gap-2"
                    >
                        <FolderPlus size={20} />
                        Create Your First Engagement
                    </button>
                </div>
            ) : filteredEngagements.length === 0 ? (
                <div className="card text-center py-12 bg-white/60 backdrop-blur-sm">
                    <Search size={48} className="mx-auto text-gray-400 mb-4" />
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                        No Results Found
                    </h3>
                    <p className="text-gray-600 mb-4">
                        No engagements match your search "{searchQuery}"
                    </p>
                    <button
                        onClick={clearSearch}
                        className="btn-secondary inline-flex items-center gap-2"
                    >
                        <X size={20} />
                        Clear Search
                    </button>
                </div>
            ) : (
                <div className="grid gap-4 max-h-[calc(100vh-320px)] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100">
                    {filteredEngagements.map((engagement) => (
                        <div
                            key={engagement.id}
                            className="card hover:shadow-md transition-all cursor-pointer group bg-white/80 backdrop-blur-sm border border-gray-200/50 hover:border-blue-300/50"
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
                                            openEditForm(engagement);
                                        }}
                                        className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                                        title="Edit engagement"
                                    >
                                        <Edit2 size={20} />
                                    </button>
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleDelete(engagement.id, engagement.name, engagement.document_count);
                                        }}
                                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                        title="Delete engagement"
                                    >
                                        <Trash2 size={20} />
                                    </button>
                                    <button
                                        onClick={() => onSelectEngagement(engagement)}
                                        className="p-2 text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                                        title="Open engagement"
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
