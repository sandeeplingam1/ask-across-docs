import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Engagements
export const engagementApi = {
    list: () => api.get('/engagements'),
    create: (data) => api.post('/engagements', data),
    get: (id) => api.get(`/engagements/${id}`),
    delete: (id) => api.delete(`/engagements/${id}`),
};

// Documents
export const documentApi = {
    list: (engagementId) => api.get(`/engagements/${engagementId}/documents`),
    upload: (engagementId, files, onProgress) => {
        const formData = new FormData();
        files.forEach(file => formData.append('files', file));

        return api.post(`/engagements/${engagementId}/documents`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            onUploadProgress: onProgress,
        });
    },
    delete: (engagementId, documentId) =>
        api.delete(`/engagements/${engagementId}/documents/${documentId}`),
};

// Questions
export const questionApi = {
    ask: (engagementId, question, options = {}) =>
        api.post(`/engagements/${engagementId}/ask`, {
            question,
            include_sources: true,
            max_sources: 5,
            ...options,
        }),

    batchAsk: (engagementId, questions) =>
        api.post(`/engagements/${engagementId}/batch-ask`, {
            questions,
            include_sources: true,
        }),

    batchAskFile: (engagementId, file) => {
        const formData = new FormData();
        formData.append('file', file);

        return api.post(`/engagements/${engagementId}/batch-ask-file`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
    },

    getHistory: (engagementId, limit = 50) =>
        api.get(`/engagements/${engagementId}/history`, { params: { limit } }),
};

export default api;
