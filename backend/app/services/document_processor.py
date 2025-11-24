"""Document processing service for extracting text from PDFs, DOCX, and TXT files"""
import io
import os
from pathlib import Path
from typing import BinaryIO, Optional
import PyPDF2
from docx import Document as DocxDocument


class DocumentProcessor:
    """Handles document parsing and text extraction"""
    
    SUPPORTED_TYPES = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".txt": "text/plain"
    }
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize document processor
        
        Args:
            chunk_size: Target size for text chunks (in characters)
            chunk_overlap: Overlap between chunks (in characters)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def is_supported(self, filename: str) -> bool:
        """Check if file type is supported"""
        ext = Path(filename).suffix.lower()
        return ext in self.SUPPORTED_TYPES
    
    def get_file_type(self, filename: str) -> str:
        """Get MIME type for file"""
        ext = Path(filename).suffix.lower()
        return self.SUPPORTED_TYPES.get(ext, "application/octet-stream")
    
    def extract_text(self, file_content: BinaryIO, filename: str) -> str:
        """
        Extract text from document (backward compatible)
        
        Args:
            file_content: File binary content
            filename: Original filename to determine type
            
        Returns:
            Extracted text content
        """
        structured_data = self.extract_with_metadata(file_content, filename)
        return structured_data['text']
    
    def extract_with_metadata(self, file_content: BinaryIO, filename: str) -> dict:
        """
        Extract text with metadata (page numbers, paragraph info)
        
        Args:
            file_content: File binary content
            filename: Original filename to determine type
            
        Returns:
            Dict with 'text' and 'pages' metadata
        """
        ext = Path(filename).suffix.lower()
        
        if ext == ".pdf":
            return self._extract_pdf_with_pages(file_content)
        elif ext in [".docx", ".doc"]:
            return self._extract_docx_with_paragraphs(file_content)
        elif ext == ".txt":
            text = self._extract_txt(file_content)
            return {
                'text': text,
                'pages': [{'page_num': 1, 'text': text, 'start_char': 0, 'end_char': len(text)}]
            }
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    
    def _extract_pdf(self, file_content: BinaryIO) -> str:
        """Extract text from PDF file (backward compatible)"""
        data = self._extract_pdf_with_pages(file_content)
        return data['text']
    
    def _extract_pdf_with_pages(self, file_content: BinaryIO) -> dict:
        """Extract text from PDF with page metadata"""
        try:
            pdf_reader = PyPDF2.PdfReader(file_content)
            text_parts = []
            pages_metadata = []
            current_char = 0
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    text = page.extract_text()
                    if text.strip():
                        page_text = f"[Page {page_num + 1}]\n{text}"
                        text_parts.append(page_text)
                        
                        # Track page metadata
                        pages_metadata.append({
                            'page_num': page_num + 1,
                            'text': text,
                            'start_char': current_char,
                            'end_char': current_char + len(page_text)
                        })
                        current_char += len(page_text) + 2  # +2 for "\n\n"
                except Exception as e:
                    print(f"Warning: Could not extract text from page {page_num + 1}: {e}")
                    continue
            
            full_text = "\n\n".join(text_parts)
            return {
                'text': full_text,
                'pages': pages_metadata
            }
        except Exception as e:
            raise ValueError(f"Failed to extract PDF: {str(e)}")
    
    def _extract_docx(self, file_content: BinaryIO) -> str:
        """Extract text from DOCX file (backward compatible)"""
        data = self._extract_docx_with_paragraphs(file_content)
        return data['text']
    
    def _extract_docx_with_paragraphs(self, file_content: BinaryIO) -> dict:
        """Extract text from DOCX with paragraph metadata"""
        try:
            doc = DocxDocument(file_content)
            paragraphs = []
            pages_metadata = []
            current_char = 0
            
            for para_num, para in enumerate(doc.paragraphs):
                if para.text.strip():
                    para_text = para.text
                    paragraphs.append(para_text)
                    
                    # Track paragraph as "page" for consistency
                    pages_metadata.append({
                        'page_num': para_num + 1,  # Paragraph number
                        'text': para_text,
                        'start_char': current_char,
                        'end_char': current_char + len(para_text)
                    })
                    current_char += len(para_text) + 2  # +2 for "\n\n"
            
            full_text = "\n\n".join(paragraphs)
            return {
                'text': full_text,
                'pages': pages_metadata
            }
        except Exception as e:
            raise ValueError(f"Failed to extract DOCX: {str(e)}")
    
    def _extract_txt(self, file_content: BinaryIO) -> str:
        """Extract text from TXT file"""
        try:
            content = file_content.read()
            # Try UTF-8 first, fall back to latin-1
            try:
                return content.decode('utf-8')
            except UnicodeDecodeError:
                return content.decode('latin-1')
        except Exception as e:
            raise ValueError(f"Failed to extract TXT: {str(e)}")
    
    def chunk_text(self, text: str, metadata: Optional[dict] = None, pages_info: Optional[list] = None) -> list[dict]:
        """
        Split text into overlapping chunks with page number tracking
        
        Args:
            text: Full text to chunk
            metadata: Optional metadata to attach to each chunk
            pages_info: Optional list of page metadata from extract_with_metadata
            
        Returns:
            List of chunks with metadata including page numbers
        """
        if not text.strip():
            return []
        
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            # Calculate end position
            end = start + self.chunk_size
            
            # If not at the end, try to break at sentence or word boundary
            if end < len(text):
                # Look for sentence end (., !, ?)
                for delimiter in ['. ', '! ', '? ', '\n\n', '\n']:
                    last_delim = text.rfind(delimiter, start, end)
                    if last_delim != -1:
                        end = last_delim + len(delimiter)
                        break
            
            # Extract chunk
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunk_data = {
                    "text": chunk_text,
                    "chunk_index": chunk_index,
                    "start_char": start,
                    "end_char": end
                }
                
                # Determine page number(s) for this chunk
                if pages_info:
                    chunk_pages = []
                    for page in pages_info:
                        # Check if chunk overlaps with this page
                        if not (end <= page['start_char'] or start >= page['end_char']):
                            chunk_pages.append(page['page_num'])
                    
                    if chunk_pages:
                        chunk_data['page_number'] = chunk_pages[0]  # Primary page
                        chunk_data['page_numbers'] = chunk_pages  # All pages it spans
                
                if metadata:
                    chunk_data.update(metadata)
                
                chunks.append(chunk_data)
                chunk_index += 1
            
            # Move start position (with overlap)
            start = end - self.chunk_overlap if end < len(text) else end
        
        return chunks
