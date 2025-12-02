import { useState } from 'react';
import QuestionTemplateList from '../components/QuestionTemplateList';
import QuestionTemplateUpload from '../components/QuestionTemplateUpload';

function QuestionTemplates() {
  const [refreshKey, setRefreshKey] = useState(0);

  const handleUploadSuccess = () => {
    // Trigger re-render of template list
    setRefreshKey(prev => prev + 1);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Question Template Library</h1>
          <p className="text-gray-600 mt-2">
            Upload and manage reusable question templates. Apply them to any engagement to save time.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Upload Form - Left Column */}
          <div className="lg:col-span-1">
            <QuestionTemplateUpload onUploadSuccess={handleUploadSuccess} />
          </div>

          {/* Template List - Right Column (2/3 width) */}
          <div className="lg:col-span-2">
            <QuestionTemplateList key={refreshKey} />
          </div>
        </div>

        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-blue-900 mb-2">💡 How to use templates</h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>1. Upload a question document (same format as engagement questions)</li>
            <li>2. Give it a descriptive name like "IT Governance Questions"</li>
            <li>3. Go to any engagement and click "Apply Template" to load the questions</li>
            <li>4. Templates are reusable across all engagements</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default QuestionTemplates;
