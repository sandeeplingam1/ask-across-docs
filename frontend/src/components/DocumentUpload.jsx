import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { documentApi } from '../api';
import { Upload, File, CheckCircle, XCircle, Loader } from 'lucide-react';

export default function DocumentUpload({ engagement, onUploadComplete }) {
    const [uploading, setUploading] = useState(false);
    const [uploadResults, setUploadResults] = useState(null);
    const [progress, setProgress] = useState(0);
    const [currentBatch, setCurrentBatch] = useState(0);
    const [totalBatches, setTotalBatches] = useState(0);

    const onDrop = useCallback(async (acceptedFiles) => {
        if (acceptedFiles.length === 0) return;

        setUploading(true);
        setUploadResults(null);
        setProgress(0);

        const BATCH_SIZE = 5; // Process 5 files at a time
        const batches = [];
        for (let i = 0; i < acceptedFiles.length; i += BATCH_SIZE) {
            batches.push(acceptedFiles.slice(i, i + BATCH_SIZE));
        }

        setTotalBatches(batches.length);

        const allResults = [];
        let successCount = 0;
        let failCount = 0;

        try {
            for (let i = 0; i < batches.length; i++) {
                setCurrentBatch(i + 1);
                const batch = batches[i];
                
                try {
                    const response = await documentApi.upload(
                        engagement.id,
                        batch,
                        (progressEvent) => {
                            const batchProgress = Math.round(
                                (progressEvent.loaded * 100) / progressEvent.total
                            );
                            const overallProgress = Math.round(
                                ((i + (batchProgress / 100)) / batches.length) * 100
                            );
                            setProgress(overallProgress);
                        }
                    );

                    allResults.push(...response.data.results);
                    successCount += response.data.successful;
                    failCount += response.data.failed;
                } catch (error) {
                    console.error(`Batch ${i + 1} failed:`, error);
                    // Mark batch files as failed
                    batch.forEach(file => {
                        allResults.push({
                            filename: file.name,
                            status: 'failed',
                            message: 'Upload error: ' + (error.response?.data?.detail || error.message)
                        });
                        failCount++;
                    });
                }

                // Small delay between batches to avoid overwhelming the server
                if (i < batches.length - 1) {
                    await new Promise(resolve => setTimeout(resolve, 1000));
                }
            }

            setUploadResults({
                total_files: acceptedFiles.length,
                successful: successCount,
                failed: failCount,
                results: allResults
            });

            if (onUploadComplete) {
                onUploadComplete();
            }
        } catch (error) {
            console.error('Upload failed:', error);
            alert('Upload failed: ' + (error.response?.data?.detail || error.message));
        } finally {
            setUploading(false);
            setCurrentBatch(0);
            setTotalBatches(0);
        }
    }, [engagement.id, onUploadComplete]);

    const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
        onDrop,
        accept: {
            'application/pdf': ['.pdf'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
            'application/msword': ['.doc'],
            'text/plain': ['.txt'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
            'application/vnd.ms-excel': ['.xls'],
            'image/png': ['.png'],
            'image/jpeg': ['.jpg', '.jpeg'],
        },
        multiple: true,
        maxSize: 100 * 1024 * 1024, // 100MB
    });

    return (
        <div className="space-y-4">
            {fileRejections.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <h4 className="text-sm font-semibold text-red-800 mb-2">
                        {fileRejections.length} file(s) rejected:
                    </h4>
                    <ul className="text-sm text-red-700 space-y-1">
                        {fileRejections.map(({ file, errors }) => (
                            <li key={file.name}>
                                <strong>{file.name}</strong> - {errors[0].code === 'file-invalid-type' ? 'Unsupported file type (only PDF, DOCX, DOC, TXT)' : errors[0].message}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
            
            <div
                {...getRootProps()}
                className={`
          border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all
          ${isDragActive ? 'border-primary-500 bg-primary-50' : 'border-gray-300 hover:border-primary-400 bg-white'}
          ${uploading ? 'cursor-not-allowed opacity-50' : ''}
        `}
            >
                <input {...getInputProps()} disabled={uploading} />

                <Upload
                    size={48}
                    className={`mx-auto mb-4 ${isDragActive ? 'text-primary-600' : 'text-gray-400'}`}
                />

                {uploading ? (
                    <div>
                        <Loader className="animate-spin mx-auto mb-2 text-primary-600" size={32} />
                        <p className="text-lg font-medium text-gray-900">
                            Uploading and processing documents...
                        </p>
                        {totalBatches > 1 && (
                            <p className="text-sm text-gray-600 mt-1">
                                Processing batch {currentBatch} of {totalBatches}
                            </p>
                        )}
                        <div className="mt-4 max-w-md mx-auto">
                            <div className="w-full bg-gray-200 rounded-full h-2">
                                <div
                                    className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                                    style={{ width: `${progress}%` }}
                                />
                            </div>
                            <p className="text-sm text-gray-600 mt-2">{progress}%</p>
                        </div>
                    </div>
                ) : (
                    <div>
                        <p className="text-lg font-medium text-gray-900 mb-2">
                            {isDragActive ? 'Drop files here' : 'Drag & drop documents here'}
                        </p>
                        <p className="text-sm text-gray-600 mb-4">
                            or click to browse
                        </p>
                        <p className="text-xs text-gray-500">
                            Supported: PDF, DOCX, DOC, TXT, XLSX, XLS, PNG, JPG • Max 100MB per file
                        </p>
                    </div>
                )}
            </div>

            {uploadResults && (
                <div className="card">
                    <h3 className="text-lg font-semibold mb-4">Upload Results</h3>

                    <div className="flex gap-4 mb-4 text-sm">
                        <span className="text-gray-600">
                            Total: <strong>{uploadResults.total_files}</strong>
                        </span>
                        <span className="text-green-600">
                            Successful: <strong>{uploadResults.successful}</strong>
                        </span>
                        {uploadResults.failed > 0 && (
                            <span className="text-red-600">
                                Failed: <strong>{uploadResults.failed}</strong>
                            </span>
                        )}
                    </div>

                    <div className="space-y-2 max-h-64 overflow-y-auto">
                        {uploadResults.results.map((result, index) => (
                            <div
                                key={index}
                                className={`
                  flex items-start gap-3 p-3 rounded-lg
                  ${result.status === 'success' ? 'bg-green-50' : 'bg-red-50'}
                `}
                            >
                                {result.status === 'success' ? (
                                    <CheckCircle className="text-green-600 flex-shrink-0 mt-0.5" size={20} />
                                ) : (
                                    <XCircle className="text-red-600 flex-shrink-0 mt-0.5" size={20} />
                                )}

                                <div className="flex-1 min-w-0">
                                    <p className="font-medium text-gray-900 truncate">
                                        {result.filename}
                                    </p>
                                    {result.message && (
                                        <p className={`text-sm ${result.status === 'success' ? 'text-green-700' : 'text-red-700'}`}>
                                            {result.message}
                                        </p>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
