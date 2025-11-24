import React, { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { X, ChevronLeft, ChevronRight, ZoomIn, ZoomOut } from 'lucide-react';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

export default function DocumentViewer({ documentId, filename, pageNumber, searchText, onClose }) {
    const [numPages, setNumPages] = useState(null);
    const [currentPage, setCurrentPage] = useState(pageNumber || 1);
    const [scale, setScale] = useState(1.0);
    const [loading, setLoading] = useState(true);

    const documentUrl = `http://localhost:8000/api/documents/${documentId}/file`;

    const onDocumentLoadSuccess = ({ numPages }) => {
        setNumPages(numPages);
        setLoading(false);
        // Navigate to the specified page if provided
        if (pageNumber && pageNumber <= numPages) {
            setCurrentPage(pageNumber);
        }
    };

    const goToPrevPage = () => {
        setCurrentPage(prev => Math.max(1, prev - 1));
    };

    const goToNextPage = () => {
        setCurrentPage(prev => Math.min(numPages || 1, prev + 1));
    };

    const zoomIn = () => {
        setScale(prev => Math.min(2.0, prev + 0.1));
    };

    const zoomOut = () => {
        setScale(prev => Math.max(0.5, prev - 0.1));
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-75 z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-2xl max-w-5xl w-full max-h-[90vh] flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-gray-200">
                    <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-lg text-gray-900 truncate">
                            {filename}
                        </h3>
                        {pageNumber && (
                            <p className="text-sm text-primary-600">
                                Viewing citation from page {pageNumber}
                            </p>
                        )}
                    </div>

                    <button
                        onClick={onClose}
                        className="ml-4 p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        <X size={24} />
                    </button>
                </div>

                {/* Controls */}
                <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50">
                    <div className="flex items-center gap-2">
                        <button
                            onClick={goToPrevPage}
                            disabled={currentPage <= 1}
                            className="p-2 hover:bg-gray-200 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            <ChevronLeft size={20} />
                        </button>

                        <span className="text-sm font-medium px-3">
                            Page {currentPage} of {numPages || '?'}
                        </span>

                        <button
                            onClick={goToNextPage}
                            disabled={currentPage >= (numPages || 1)}
                            className="p-2 hover:bg-gray-200 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            <ChevronRight size={20} />
                        </button>
                    </div>

                    <div className="flex items-center gap-2">
                        <button
                            onClick={zoomOut}
                            disabled={scale <= 0.5}
                            className="p-2 hover:bg-gray-200 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            <ZoomOut size={20} />
                        </button>

                        <span className="text-sm font-medium px-3">
                            {Math.round(scale * 100)}%
                        </span>

                        <button
                            onClick={zoomIn}
                            disabled={scale >= 2.0}
                            className="p-2 hover:bg-gray-200 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            <ZoomIn size={20} />
                        </button>
                    </div>
                </div>

                {/* PDF Viewer */}
                <div className="flex-1 overflow-auto p-4 bg-gray-100">
                    {loading && (
                        <div className="flex items-center justify-center h-full">
                            <div className="text-gray-500">Loading document...</div>
                        </div>
                    )}

                    <div className="flex justify-center">
                        <Document
                            file={documentUrl}
                            onLoadSuccess={onDocumentLoadSuccess}
                            loading={<div className="text-gray-500">Loading PDF...</div>}
                            error={<div className="text-red-600">Failed to load PDF</div>}
                        >
                            <Page
                                pageNumber={currentPage}
                                scale={scale}
                                renderTextLayer={true}
                                renderAnnotationLayer={true}
                                customTextRenderer={searchText ? (textItem) => {
                                    // Highlight search text if provided
                                    if (textItem.str.toLowerCase().includes(searchText.toLowerCase())) {
                                        return (
                                            <mark style={{ backgroundColor: 'yellow' }}>
                                                {textItem.str}
                                            </mark>
                                        );
                                    }
                                    return textItem.str;
                                } : undefined}
                            />
                        </Document>
                    </div>
                </div>
            </div>
        </div>
    );
}
