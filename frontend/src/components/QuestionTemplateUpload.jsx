import { useState } from 'react';
import api from '../api';

function QuestionTemplateUpload({ onUploadSuccess }) {
  const [uploading, setUploading] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    file: null
  });
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setFormData({ ...formData, file });
      setError(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.name.trim()) {
      setError('Template name is required');
      return;
    }
    
    if (!formData.file) {
      setError('Please select a file');
      return;
    }

    try {
      setUploading(true);
      setError(null);

      const result = await api.uploadQuestionTemplate(
        formData.name,
        formData.description,
        formData.file
      );

      // Reset form
      setFormData({ name: '', description: '', file: null });
      
      // Clear file input
      const fileInput = document.getElementById('template-file-input');
      if (fileInput) fileInput.value = '';

      if (onUploadSuccess) {
        onUploadSuccess(result);
      }

      alert(`Template "${result.name}" uploaded successfully with ${result.question_count} questions!`);
    } catch (err) {
      console.error('Failed to upload template:', err);
      setError(err.message || 'Failed to upload template. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Upload New Template</h3>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Template Name *
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="e.g., IT Governance Questions"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={uploading}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description (optional)
          </label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            placeholder="Brief description of what this template covers..."
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={uploading}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Question File *
          </label>
          <input
            id="template-file-input"
            type="file"
            accept=".txt,.docx,.doc"
            onChange={handleFileChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={uploading}
          />
          <p className="text-xs text-gray-500 mt-1">
            Supported formats: .txt, .docx, .doc
          </p>
          {formData.file && (
            <p className="text-sm text-green-600 mt-1">
              Selected: {formData.file.name}
            </p>
          )}
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        <button
          type="submit"
          disabled={uploading}
          className={`w-full px-4 py-2 rounded-md font-medium ${
            uploading
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }`}
        >
          {uploading ? 'Uploading...' : 'Upload Template'}
        </button>
      </form>
    </div>
  );
}

export default QuestionTemplateUpload;
