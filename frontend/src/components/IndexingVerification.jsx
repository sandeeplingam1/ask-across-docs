import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, AlertTriangle, RefreshCw, Database, Search } from 'lucide-react';

export default function IndexingVerification({ engagementId }) {
  const [verification, setVerification] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  const verifyIndexing = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || 'https://auditapp-staging-backend.graydune-dadabae1.eastus.azurecontainerapps.io'}/api/engagements/${engagementId}/documents/verify-indexing`
      );
      
      if (!response.ok) {
        console.error('Verification API returned:', response.status);
        setVerification(null);
        return;
      }
      
      const data = await response.json();
      
      // Validate data structure
      if (!data || !data.summary) {
        console.error('Invalid verification data:', data);
        setVerification(null);
        return;
      }
      
      setVerification(data);
    } catch (error) {
      console.error('Failed to verify indexing:', error);
      setVerification(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (engagementId) {
      verifyIndexing();
    }
  }, [engagementId]);

  if (!verification && !loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Search className="w-5 h-5 text-gray-400" />
            <span className="text-sm text-gray-600">AI Search Verification</span>
          </div>
          <button
            onClick={verifyIndexing}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
          >
            Verify Indexing
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center gap-2">
          <RefreshCw className="w-5 h-5 animate-spin text-blue-600" />
          <span className="text-sm text-gray-600">Verifying AI Search index...</span>
        </div>
      </div>
    );
  }

  if (!verification || !verification.summary || verification.summary.total_documents === 0) {
    return null;
  }

  const { summary, issues } = verification;
  const allVerified = summary.verified === summary.total_documents;
  const hasIssues = issues && issues.length > 0;

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Search className="w-5 h-5 text-gray-700" />
          <h3 className="font-semibold text-gray-900">AI Search Index Status</h3>
        </div>
        <button
          onClick={verifyIndexing}
          disabled={loading}
          className="text-sm text-blue-600 hover:text-blue-700 font-medium disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 inline mr-1 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-4 mb-4">
        <div className="text-center p-3 bg-gray-50 rounded-lg">
          <div className="text-2xl font-bold text-gray-900">{summary.total_documents}</div>
          <div className="text-xs text-gray-600">Total Docs</div>
        </div>
        <div className="text-center p-3 bg-green-50 rounded-lg">
          <div className="flex items-center justify-center gap-1">
            <CheckCircle className="w-5 h-5 text-green-600" />
            <div className="text-2xl font-bold text-green-700">{summary.verified}</div>
          </div>
          <div className="text-xs text-gray-600">Verified</div>
        </div>
        <div className="text-center p-3 bg-yellow-50 rounded-lg">
          <div className="flex items-center justify-center gap-1">
            <AlertTriangle className="w-5 h-5 text-yellow-600" />
            <div className="text-2xl font-bold text-yellow-700">{summary.mismatch}</div>
          </div>
          <div className="text-xs text-gray-600">Mismatch</div>
        </div>
        <div className="text-center p-3 bg-red-50 rounded-lg">
          <div className="flex items-center justify-center gap-1">
            <XCircle className="w-5 h-5 text-red-600" />
            <div className="text-2xl font-bold text-red-700">{summary.missing_chunks}</div>
          </div>
          <div className="text-xs text-gray-600">Missing</div>
        </div>
      </div>

      {/* Overall Status */}
      <div className={`flex items-center gap-2 p-3 rounded-lg ${
        allVerified ? 'bg-green-50 border border-green-200' : 
        hasIssues ? 'bg-yellow-50 border border-yellow-200' : 
        'bg-gray-50 border border-gray-200'
      }`}>
        {allVerified ? (
          <>
            <CheckCircle className="w-5 h-5 text-green-600" />
            <div>
              <div className="font-semibold text-green-900">All documents verified in AI Search</div>
              <div className="text-sm text-green-700">{summary.percentage_verified}% of chunks indexed and searchable</div>
            </div>
          </>
        ) : (
          <>
            <AlertTriangle className="w-5 h-5 text-yellow-600" />
            <div>
              <div className="font-semibold text-yellow-900">
                {summary.verified}/{summary.total_documents} documents verified
              </div>
              <div className="text-sm text-yellow-700">
                {summary.percentage_verified}% indexed - {issues.length} issue(s) found
              </div>
            </div>
          </>
        )}
      </div>

      {/* Issues Details */}
      {hasIssues && (
        <div className="mt-4">
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="text-sm text-gray-700 hover:text-gray-900 font-medium mb-2"
          >
            {showDetails ? '▼' : '▶'} Show Issues ({issues.length})
          </button>
          
          {showDetails && (
            <div className="space-y-2">
              {issues.map((issue, index) => (
                <div key={index} className="bg-yellow-50 border border-yellow-200 rounded p-3">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 text-yellow-600 mt-0.5 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-gray-900 truncate">{issue.filename}</div>
                      <div className="text-sm text-gray-600">{issue.issue}</div>
                      <div className="flex gap-4 mt-1 text-xs text-gray-500">
                        <span className="flex items-center gap-1">
                          <Database className="w-3 h-3" />
                          DB: {issue.db_chunks} chunks
                        </span>
                        <span className="flex items-center gap-1">
                          <Search className="w-3 h-3" />
                          AI Search: {issue.ai_search_chunks} chunks
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
