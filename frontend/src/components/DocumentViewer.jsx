import React, { useState, useEffect, useRef } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import mammoth from 'mammoth';
import { X, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, FileText, Download } from 'lucide-react';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

export default function DocumentViewer({ documentId, filename, pageNumber, searchText, onClose }) {
    const [numPages, setNumPages] = useState(null);
    const [currentPage, setCurrentPage] = useState(pageNumber || 1);
    const [scale, setScale] = useState(1.0);
    const [loading, setLoading] = useState(true);
    const [textContent, setTextContent] = useState('');
    const [docxHtml, setDocxHtml] = useState('');
    const [error, setError] = useState(null);
    const contentRef = useRef(null);

    // Use environment variable or production backend URL
    const backendUrl = import.meta.env.VITE_API_URL || 'https://auditapp-staging-backend.graydune-dadabae1.eastus.azurecontainerapps.io';
    const documentUrl = `${backendUrl}/api/documents/${documentId}/file`;
    
    // Determine file type from filename
    const fileExtension = filename.split('.').pop().toLowerCase();
    const isPdf = fileExtension === 'pdf';
    const isTextBased = ['txt', 'md', 'csv', 'json', 'xml'].includes(fileExtension);
    const isDocx = fileExtension === 'docx';
    const isOfficeDoc = ['doc', 'xlsx', 'xls', 'pptx', 'ppt'].includes(fileExtension);
    
    useEffect(() => {
        // For DOCX files, convert to HTML with Mammoth
        if (isDocx) {
            setLoading(true);
            setError(null);
            console.log('Loading DOCX document:', documentUrl);
            
            fetch(documentUrl)
                .then(response => {
                    console.log('Fetch response:', response.status);
                    if (!response.ok) throw new Error('Failed to load document');
                    return response.arrayBuffer();
                })
                .then(arrayBuffer => {
                    console.log('Got arrayBuffer, size:', arrayBuffer.byteLength);
                    return mammoth.convertToHtml({ arrayBuffer });
                })
                .then(result => {
                    console.log('Mammoth conversion complete, HTML length:', result.value.length);
                    if (result.messages && result.messages.length > 0) {
                        console.log('Mammoth messages:', result.messages);
                    }
                    setDocxHtml(result.value);
                    setLoading(false);
                })
                .catch(err => {
                    console.error('Error loading DOCX:', err);
                    setError(err.message);
                    setLoading(false);
                });
        } else if (isTextBased) {
            // For text files, fetch directly
            fetch(documentUrl)
                .then(response => {
                    if (!response.ok) throw new Error('Failed to load document');
                    return response.text();
                })
                .then(text => {
                    setTextContent(text);
                    setLoading(false);
                })
                .catch(err => {
                    setError(err.message);
                    setLoading(false);
                });
        } else if (isOfficeDoc) {
            // For other Office docs, mark as loaded
            setLoading(false);
        }
    }, [documentUrl, isTextBased, isDocx, isOfficeDoc]);
    
    // Highlight search text in DOCX and text documents - enhanced to find partial matches
    useEffect(() => {
        if (!searchText || typeof searchText !== 'string' || !contentRef.current) return;
        
        const content = contentRef.current;
        const text = content.textContent || content.innerText;
        
        if (!text || typeof text !== 'string') return;
        
        // Try to find the search text with flexible matching
        const searchCleaned = String(searchText)
            .replace(/\s+/g, ' ') // Normalize whitespace
            .trim()
            .toLowerCase();
        
        const textCleaned = String(text)
            .replace(/\s+/g, ' ')
            .toLowerCase();
        
        // Try to find exact match first, then try first 100 chars, then first 50 chars
        let searchPhrase = searchCleaned;
        let phraseIndex = textCleaned.indexOf(searchPhrase);
        
        if (phraseIndex === -1 && searchCleaned.length > 100) {
            searchPhrase = searchCleaned.substring(0, 100);
            phraseIndex = textCleaned.indexOf(searchPhrase);
        }
        
        if (phraseIndex === -1 && searchCleaned.length > 50) {
            searchPhrase = searchCleaned.substring(0, 50);
            phraseIndex = textCleaned.indexOf(searchPhrase);
        }
        
        if (phraseIndex !== -1) {
            // Use CSS to highlight matching text with better styling
            const walker = document.createTreeWalker(
                content,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );
            
            const textNodes = [];
            let node;
            while (node = walker.nextNode()) {
                textNodes.push(node);
            }
            
            let foundMatch = false;
            
            textNodes.forEach(textNode => {
                if (foundMatch) return; // Only highlight first match
                
                const nodeText = textNode.textContent;
                const nodeCleaned = nodeText.replace(/\s+/g, ' ').toLowerCase();
                const nodeIndex = nodeCleaned.indexOf(searchPhrase);
                
                if (nodeIndex !== -1) {
                    const before = nodeText.substring(0, nodeIndex);
                    const matchLength = searchPhrase.length;
                    const match = nodeText.substring(nodeIndex, nodeIndex + matchLength);
                    const after = nodeText.substring(nodeIndex + matchLength);
                    
                    const span = document.createElement('span');
                    span.innerHTML = `${before}<mark style="background-color: #ffd700; padding: 4px 8px; border-radius: 4px; font-weight: 600; box-shadow: 0 2px 4px rgba(0,0,0,0.1); animation: pulse 2s ease-in-out 3;">${match}</mark>${after}`;
                    
                    textNode.parentNode.replaceChild(span, textNode);
                    foundMatch = true;
                }
            });
            
            // Scroll to first highlight with delay for rendering
            setTimeout(() => {
                const firstMark = content.querySelector('mark');
                if (firstMark) {
                    firstMark.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    // Add pulsing animation
                    firstMark.style.animation = 'pulse 1s ease-in-out 3';
                }
            }, 100);
        }
    }, [searchText, docxHtml, textContent]);

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

                {/* Download button - hide the separate one and keep it in header */}
                <div className="flex items-center justify-between p-3 border-b border-gray-200 bg-gray-50">
                    <div className="text-sm text-gray-600">
                        {isDocx && 'Word Document with formatting preserved'}
                        {isPdf && 'PDF Document'}
                        {isTextBased && 'Text Document'}
                        {isOfficeDoc && 'Office Document'}
                    </div>
                    <a
                        href={documentUrl}
                        download={filename}
                        className="flex items-center gap-2 px-3 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
                    >
                        <Download size={16} />
                        Download
                    </a>
                </div>

                {/* Controls - only show for PDFs */}
                {isPdf && (
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
                )}

                {/* Document Viewer */}
                <div className="flex-1 overflow-hidden bg-gray-100">
                    {loading && (
                        <div className="flex items-center justify-center h-full">
                            <div className="text-center">
                                <div className="text-gray-500 mb-2">Loading document...</div>
                                <div className="text-sm text-gray-400">
                                    {isPdf && 'Loading PDF...'}
                                    {isDocx && 'Converting DOCX...'}
                                    {isTextBased && 'Loading text...'}
                                </div>
                            </div>
                        </div>
                    )}
                    
                    {error && (
                        <div className="flex flex-col items-center justify-center h-full gap-4">
                            <FileText size={48} className="text-gray-400" />
                            <div className="text-red-600">{error}</div>
                            <a 
                                href={documentUrl}
                                download={filename}
                                className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                            >
                                <Download size={16} />
                                Download File
                            </a>
                        </div>
                    )}

                    {/* PDF Viewer */}
                    {!error && isPdf && (
                        <div className="flex justify-center h-full overflow-auto p-4">
                            <Document
                                file={documentUrl}
                                onLoadSuccess={onDocumentLoadSuccess}
                                loading={<div className="text-gray-500">Loading PDF...</div>}
                                error={
                                    <div className="text-center">
                                        <div className="text-red-600 mb-4">Failed to load PDF</div>
                                        <a 
                                            href={documentUrl}
                                            download={filename}
                                            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                                        >
                                            <Download size={16} />
                                            Download File
                                        </a>
                                    </div>
                                }
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
                    )}
                    
                    {/* DOCX Document Viewer with formatting */}
                    {!loading && !error && isDocx && docxHtml && (
                        <div className="h-full overflow-auto p-8">
                            <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-sm p-12">
                                <div 
                                    ref={contentRef}
                                    className="prose prose-sm max-w-none"
                                    dangerouslySetInnerHTML={{ __html: docxHtml }}
                                    style={{
                                        fontFamily: '"Calibri", "Arial", sans-serif',
                                        lineHeight: '1.6',
                                        color: '#000'
                                    }}
                                />
                            </div>
                        </div>
                    )}
                    
                    {/* Office Document Viewer (DOC, XLSX, PPTX) */}
                    {!loading && !error && isOfficeDoc && (
                        <div className="h-full w-full flex flex-col items-center justify-center bg-white p-8">
                            <div className="text-center mb-6">
                                <FileText size={64} className="text-primary-600 mx-auto mb-4" />
                                <h3 className="text-xl font-semibold text-gray-900 mb-2">{filename}</h3>
                                <p className="text-gray-600 mb-4">
                                    This is a {fileExtension.toUpperCase()} document
                                </p>
                                <p className="text-sm text-gray-500 mb-6">
                                    Office documents are best viewed by downloading or opening in their native application
                                </p>
                            </div>
                            <div className="flex gap-3">
                                <a 
                                    href={documentUrl}
                                    download={filename}
                                    className="flex items-center gap-2 px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium"
                                >
                                    <Download size={20} />
                                    Download File
                                </a>
                                <a 
                                    href={documentUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-2 px-6 py-3 border-2 border-primary-600 text-primary-600 rounded-lg hover:bg-primary-50 font-medium"
                                >
                                    Open in New Tab
                                </a>
                            </div>
                        </div>
                    )}
                    
                    {/* Text File Viewer */}
                    {!loading && !error && isTextBased && (
                        <div className="h-full overflow-auto p-8">
                            <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-sm p-8">
                                <div ref={contentRef} className="prose prose-sm max-w-none">
                                    <pre className="whitespace-pre-wrap font-mono text-sm text-gray-800 leading-relaxed">
                                        {textContent}
                                    </pre>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
