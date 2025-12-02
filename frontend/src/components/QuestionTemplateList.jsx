import { useState, useEffect } from 'react';
import api from '../api';

function QuestionTemplateList({ onSelectTemplate }) {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [viewingQuestions, setViewingQuestions] = useState(false);
  const [templateQuestions, setTemplateQuestions] = useState([]);

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.listQuestionTemplates();
      setTemplates(data);
    } catch (err) {
      console.error('Failed to load question templates:', err);
      setError('Failed to load templates. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleViewQuestions = async (template) => {
    try {
      const data = await api.getQuestionTemplate(template.id);
      setTemplateQuestions(data.questions || []);
      setSelectedTemplate(template);
      setViewingQuestions(true);
    } catch (err) {
      console.error('Failed to load template questions:', err);
      alert('Failed to load questions');
    }
  };

  const handleDeleteTemplate = async (template) => {
    if (!confirm(`Delete template "${template.name}"? This cannot be undone.`)) {
      return;
    }

    try {
      await api.deleteQuestionTemplate(template.id);
      await loadTemplates();
      alert('Template deleted successfully');
    } catch (err) {
      console.error('Failed to delete template:', err);
      alert('Failed to delete template');
    }
  };

  const handleSelectForEngagement = (template) => {
    if (onSelectTemplate) {
      onSelectTemplate(template);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-20 bg-gray-200 rounded"></div>
            <div className="h-20 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-red-600">{error}</div>
        <button
          onClick={loadTemplates}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  if (viewingQuestions && selectedTemplate) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-xl font-semibold text-gray-900">
              {selectedTemplate.name}
            </h3>
            {selectedTemplate.description && (
              <p className="text-sm text-gray-600 mt-1">{selectedTemplate.description}</p>
            )}
          </div>
          <button
            onClick={() => setViewingQuestions(false)}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
          >
            Back to Templates
          </button>
        </div>

        <div className="border-t pt-4">
          <p className="text-sm text-gray-600 mb-4">
            {templateQuestions.length} question{templateQuestions.length !== 1 ? 's' : ''}
          </p>
          
          {templateQuestions.length === 0 ? (
            <p className="text-gray-500 italic">No questions found in this template</p>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {templateQuestions.map((question, index) => (
                <div key={index} className="p-3 bg-gray-50 rounded border">
                  <span className="text-sm text-gray-500 mr-2">Q{index + 1}:</span>
                  <span className="text-gray-900">{question}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Question Templates</h3>
        <span className="text-sm text-gray-600">
          {templates.length} template{templates.length !== 1 ? 's' : ''}
        </span>
      </div>

      {templates.length === 0 ? (
        <p className="text-gray-500 text-center py-8">
          No question templates yet. Upload one to get started.
        </p>
      ) : (
        <div className="space-y-3">
          {templates.map((template) => (
            <div
              key={template.id}
              className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h4 className="font-medium text-gray-900">{template.name}</h4>
                  {template.description && (
                    <p className="text-sm text-gray-600 mt-1">{template.description}</p>
                  )}
                  <div className="flex flex-wrap gap-4 mt-2 text-xs text-gray-500">
                    <span>📄 {template.filename}</span>
                    <span>📊 {template.question_count} questions</span>
                    <span>💾 {formatFileSize(template.file_size)}</span>
                    <span>📅 {formatDate(template.created_at)}</span>
                  </div>
                </div>
                
                <div className="flex gap-2 ml-4">
                  <button
                    onClick={() => handleViewQuestions(template)}
                    className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                    title="View questions"
                  >
                    View
                  </button>
                  {onSelectTemplate && (
                    <button
                      onClick={() => handleSelectForEngagement(template)}
                      className="px-3 py-1 text-sm bg-green-100 text-green-700 rounded hover:bg-green-200"
                      title="Apply to engagement"
                    >
                      Apply
                    </button>
                  )}
                  <button
                    onClick={() => handleDeleteTemplate(template)}
                    className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200"
                    title="Delete template"
                  >
                    Delete
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

export default QuestionTemplateList;
