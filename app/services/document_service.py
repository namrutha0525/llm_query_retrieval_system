import logging
import asyncio
import hashlib
import requests
import tempfile
import os
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import PyPDF2
import pdfplumber
from io import BytesIO
from datetime import datetime

from config.config import settings
from app.models.schemas import DocumentChunk, DocumentMetadata

logger = logging.getLogger(__name__)

class DocumentProcessingService:
    """Service for processing and extracting text from documents"""

    def __init__(self):
        """Initialize document processing service"""
        self.max_file_size = settings.MAX_FILE_SIZE
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP

    async def process_document_from_url(self, document_url: str) -> tuple[List[DocumentChunk], DocumentMetadata]:
        """Download and process document from URL"""

        # Generate document ID from URL
        document_id = self._generate_document_id(document_url)

        try:
            # Download document
            logger.info(f"Downloading document from: {document_url}")
            document_data = await self._download_document(document_url)

            # Extract filename from URL
            parsed_url = urlparse(document_url)
            filename = os.path.basename(parsed_url.path) or "document.pdf"

            # Create metadata
            metadata = DocumentMetadata(
                document_id=document_id,
                filename=filename,
                file_size=len(document_data),
                mime_type="application/pdf",
                upload_time=datetime.now(),
                processed=False,
                chunk_count=0
            )

            # Extract text from PDF
            logger.info(f"Extracting text from document: {filename}")
            extracted_text = await self._extract_text_from_pdf(document_data)

            # Create chunks
            logger.info(f"Creating chunks for document: {filename}")
            chunks = await self._create_chunks(extracted_text, document_id)

            # Update metadata
            metadata.processed = True
            metadata.chunk_count = len(chunks)

            logger.info(f"Successfully processed document: {filename} ({len(chunks)} chunks)")
            return chunks, metadata

        except Exception as e:
            logger.error(f"Error processing document from URL {document_url}: {e}")
            raise

    async def _download_document(self, url: str) -> bytes:
        """Download document from URL"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            if len(response.content) > self.max_file_size:
                raise ValueError(f"Document size exceeds maximum allowed size ({self.max_file_size} bytes)")

            return response.content

        except requests.RequestException as e:
            raise Exception(f"Failed to download document: {e}")

    async def _extract_text_from_pdf(self, pdf_data: bytes) -> List[Dict[str, Any]]:
        """Extract text from PDF with page and section information"""

        text_data = []

        try:
            # Use pdfplumber for better text extraction
            with pdfplumber.open(BytesIO(pdf_data)) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()

                    if page_text:
                        # Try to identify sections within the page
                        sections = self._identify_sections(page_text, page_num)
                        text_data.extend(sections)

        except Exception as e:
            logger.warning(f"pdfplumber extraction failed, trying PyPDF2: {e}")

            # Fallback to PyPDF2
            try:
                pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_data))

                for page_num, page in enumerate(pdf_reader.pages, 1):
                    page_text = page.extract_text()

                    if page_text:
                        text_data.append({
                            'text': page_text,
                            'page_number': page_num,
                            'section': f'Page {page_num}',
                            'metadata': {}
                        })

            except Exception as e2:
                raise Exception(f"Failed to extract text from PDF: {e2}")

        if not text_data:
            raise Exception("No text content could be extracted from the PDF")

        return text_data

    def _identify_sections(self, page_text: str, page_num: int) -> List[Dict[str, Any]]:
        """Identify sections within a page based on text patterns"""

        sections = []

        # Common section headers in insurance/legal documents
        section_patterns = [
            'COVERAGE', 'EXCLUSIONS', 'DEFINITIONS', 'CONDITIONS', 
            'BENEFITS', 'LIMITATIONS', 'WAITING PERIOD', 'CLAIMS',
            'PREMIUM', 'DEDUCTIBLE', 'TERMINATION', 'RENEWAL'
        ]

        lines = page_text.split('\n')
        current_section = f'Page {page_num}'
        current_text = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if line is a section header
            is_section_header = False
            for pattern in section_patterns:
                if pattern.lower() in line.lower() and len(line) < 100:
                    # Save previous section if it has content
                    if current_text:
                        sections.append({
                            'text': '\n'.join(current_text),
                            'page_number': page_num,
                            'section': current_section,
                            'metadata': {'section_type': 'content'}
                        })

                    # Start new section
                    current_section = line
                    current_text = []
                    is_section_header = True
                    break

            if not is_section_header:
                current_text.append(line)

        # Add final section
        if current_text:
            sections.append({
                'text': '\n'.join(current_text),
                'page_number': page_num,
                'section': current_section,
                'metadata': {'section_type': 'content'}
            })

        # If no sections were identified, return the whole page
        if not sections:
            sections.append({
                'text': page_text,
                'page_number': page_num,
                'section': f'Page {page_num}',
                'metadata': {'section_type': 'full_page'}
            })

        return sections

    async def _create_chunks(self, text_data: List[Dict[str, Any]], document_id: str) -> List[DocumentChunk]:
        """Create text chunks with overlap for better retrieval"""

        chunks = []
        chunk_counter = 0

        for text_item in text_data:
            text = text_item['text']
            page_number = text_item['page_number']
            section = text_item['section']
            metadata = text_item['metadata']

            # Split text into sentences for better chunking
            sentences = self._split_into_sentences(text)

            current_chunk = []
            current_length = 0

            for sentence in sentences:
                sentence_length = len(sentence)

                # If adding this sentence exceeds chunk size, save current chunk
                if current_length + sentence_length > self.chunk_size and current_chunk:
                    chunk_text = ' '.join(current_chunk)

                    chunk = DocumentChunk(
                        text=chunk_text,
                        chunk_id=f"{document_id}_chunk_{chunk_counter}",
                        document_id=document_id,
                        page_number=page_number,
                        section=section,
                        metadata={
                            **metadata,
                            'chunk_index': chunk_counter,
                            'word_count': len(chunk_text.split())
                        }
                    )
                    chunks.append(chunk)
                    chunk_counter += 1

                    # Start new chunk with overlap
                    if self.chunk_overlap > 0:
                        overlap_sentences = current_chunk[-self.chunk_overlap//50:]  # Rough overlap
                        current_chunk = overlap_sentences + [sentence]
                        current_length = sum(len(s) for s in current_chunk)
                    else:
                        current_chunk = [sentence]
                        current_length = sentence_length
                else:
                    current_chunk.append(sentence)
                    current_length += sentence_length

            # Add remaining content as final chunk
            if current_chunk:
                chunk_text = ' '.join(current_chunk)

                chunk = DocumentChunk(
                    text=chunk_text,
                    chunk_id=f"{document_id}_chunk_{chunk_counter}",
                    document_id=document_id,
                    page_number=page_number,
                    section=section,
                    metadata={
                        **metadata,
                        'chunk_index': chunk_counter,
                        'word_count': len(chunk_text.split())
                    }
                )
                chunks.append(chunk)
                chunk_counter += 1

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        import re

        # Simple sentence splitting - could be improved with NLP libraries
        sentences = re.split(r'[.!?]+', text)

        # Clean and filter sentences
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  # Filter out very short fragments
                cleaned_sentences.append(sentence)

        return cleaned_sentences

    def _generate_document_id(self, url: str) -> str:
        """Generate unique document ID from URL"""
        return hashlib.md5(url.encode()).hexdigest()[:16]

    async def validate_document_url(self, url: str) -> bool:
        """Validate if document URL is accessible and valid"""
        try:
            response = requests.head(url, timeout=10)
            return response.status_code == 200
        except:
            return False
