import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
    baseURL: `${API_BASE_URL}/api`,
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 300000, // 5 minute timeout for large batch uploads
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
    processQueued: (engagementId) =>
        api.post(`/engagements/${engagementId}/documents/process-queued`),
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

// Question Templates
export const questionTemplateApi = {
    list: () => api.get('/question-templates/'),
    get: (templateId) => api.get(`/question-templates/${templateId}/`),
    upload: (name, description, file) => {
        const formData = new FormData();
        formData.append('name', name);
        if (description) formData.append('description', description);
        formData.append('file', file);

        return api.post('/question-templates/', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
    },
    delete: (templateId) => api.delete(`/question-templates/${templateId}/`),
    applyToEngagement: (templateId, engagementId) =>
        api.post(`/question-templates/${templateId}/apply/${engagementId}/`),
};

export default {
    ...api,
    // Convenience exports
    listEngagements: () => engagementApi.list().then(res => res.data),
    createEngagement: (data) => engagementApi.create(data).then(res => res.data),
    getEngagement: (id) => engagementApi.get(id).then(res => res.data),
    deleteEngagement: (id) => engagementApi.delete(id).then(res => res.data),
    
    listDocuments: (engagementId) => documentApi.list(engagementId).then(res => res.data),
    uploadDocuments: (engagementId, files, onProgress) =>
        documentApi.upload(engagementId, files, onProgress).then(res => res.data),
    processQueuedDocuments: (engagementId) =>
        documentApi.processQueued(engagementId).then(res => res.data),
    deleteDocument: (engagementId, documentId) =>
        documentApi.delete(engagementId, documentId).then(res => res.data),
    
    askQuestion: (engagementId, question, options) =>
        questionApi.ask(engagementId, question, options).then(res => res.data),
    batchAskQuestions: (engagementId, questions) =>
        questionApi.batchAsk(engagementId, questions).then(res => res.data),
    batchAskFile: (engagementId, file) =>
        questionApi.batchAskFile(engagementId, file).then(res => res.data),
    getQuestionHistory: (engagementId, limit) =>
        questionApi.getHistory(engagementId, limit).then(res => res.data),
    
    listQuestionTemplates: () => questionTemplateApi.list().then(res => res.data),
    getQuestionTemplate: (templateId) =>
        questionTemplateApi.get(templateId).then(res => res.data),
    uploadQuestionTemplate: (name, description, file) =>
        questionTemplateApi.upload(name, description, file).then(res => res.data),
    deleteQuestionTemplate: (templateId) =>
        questionTemplateApi.delete(templateId).then(res => res.data),
    applyTemplateToEngagement: (templateId, engagementId) =>
        questionTemplateApi.applyToEngagement(templateId, engagementId).then(res => res.data),
};
/* Build 1764619277 */
