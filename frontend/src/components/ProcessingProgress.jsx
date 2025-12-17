import { useEffect, useState } from 'react';
import { CheckCircle, Clock, AlertCircle, Loader2, FileText } from 'lucide-react';
import { progressApi } from '../api';

export default function ProcessingProgress({ engagementId }) {
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!engagementId) return;

    const fetchProgress = async () => {
      try {
        const response = await progressApi.get(engagementId);
        setProgress(response.data);
        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch progress:', error);
        setLoading(false);
      }
    };

    // Fetch immediately
    fetchProgress();

    // Then poll every 5 seconds
    const interval = setInterval(fetchProgress, 5000);

    return () => clearInterval(interval);
  }, [engagementId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!progress || progress.total_documents === 0) {
    return null;
  }

  const { completed, processing, queued, failed, total_documents, overall_progress, estimated_time_remaining_seconds, currently_processing } = progress;

  // Show progress bar only if there are documents being processed or queued
  if (processing === 0 && queued === 0 && failed === 0) {
    return null; // All done, no need to show
  }

  const formatTime = (seconds) => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.ceil(seconds / 60)}m`;
    return `${Math.ceil(seconds / 3600)}h ${Math.ceil((seconds % 3600) / 60)}m`;
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Processing Progress</h3>
        {estimated_time_remaining_seconds > 0 && (
          <span className="text-sm text-gray-600">
            Est. {formatTime(estimated_time_remaining_seconds)} remaining
          </span>
        )}
      </div>

      {/* Overall Progress Bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">
            {completed} of {total_documents} documents completed
          </span>
          <span className="text-sm font-semibold text-gray-900">{overall_progress}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2.5">
          <div
            className="bg-blue-600 h-2.5 rounded-full transition-all duration-500"
            style={{ width: `${overall_progress}%` }}
          ></div>
        </div>
      </div>

      {/* Status Breakdown */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="flex items-center space-x-2">
          <CheckCircle className="w-5 h-5 text-green-600" />
          <div>
            <div className="text-2xl font-bold text-gray-900">{completed}</div>
            <div className="text-xs text-gray-600">Completed</div>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
          <div>
            <div className="text-2xl font-bold text-gray-900">{processing}</div>
            <div className="text-xs text-gray-600">Processing</div>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Clock className="w-5 h-5 text-yellow-600" />
          <div>
            <div className="text-2xl font-bold text-gray-900">{queued}</div>
            <div className="text-xs text-gray-600">Queued</div>
          </div>
        </div>

        {failed > 0 && (
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-red-600" />
            <div>
              <div className="text-2xl font-bold text-gray-900">{failed}</div>
              <div className="text-xs text-gray-600">Failed</div>
            </div>
          </div>
        )}
      </div>

      {/* Currently Processing Documents */}
      {currently_processing && currently_processing.length > 0 && (
        <div className="border-t pt-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Currently Processing:</h4>
          <div className="space-y-3">
            {currently_processing.map((doc) => (
              <div key={doc.id} className="bg-gray-50 rounded-lg p-3">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center space-x-2 flex-1 min-w-0">
                    <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
                    <span className="text-sm font-medium text-gray-900 truncate">
                      {doc.filename}
                    </span>
                  </div>
                  <span className="text-xs font-semibold text-gray-700 ml-2">
                    {doc.progress}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-1.5 mb-1">
                  <div
                    className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                    style={{ width: `${doc.progress}%` }}
                  ></div>
                </div>
                <div className="text-xs text-gray-600">{doc.status_detail}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Info message */}
      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-800">
          <strong>Note:</strong> Documents are being processed in the background. You can continue
          working and the page will automatically update as documents complete.
        </p>
      </div>
    </div>
  );
}
