"""PDF text extraction with pdfplumber and pypdf fallback."""

import re
from pathlib import Path
from typing import Dict, List, Optional

import pdfplumber
import pypdf

from ..utils.exceptions import PDFExtractionError
from ..utils.logger import get_logger

logger = get_logger("pdf_extractor")


class PDFExtractor:
    """Extract text and metadata from PDF files."""

    def __init__(self, pdf_path: Path):
        """
        Initialize PDF extractor.

        Args:
            pdf_path: Path to PDF file
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise PDFExtractionError(
                f"PDF file not found: {pdf_path}", pdf_path=str(pdf_path)
            )
        if not self.pdf_path.is_file():
            raise PDFExtractionError(
                f"Path is not a file: {pdf_path}", pdf_path=str(pdf_path)
            )

    def extract(self) -> Dict:
        """
        Extract text and metadata from PDF.

        Returns:
            Dictionary with keys: text, metadata, page_count

        Raises:
            PDFExtractionError: If extraction fails with both methods
        """
        logger.info(f"Extracting text from {self.pdf_path.name}")

        try:
            return self._extract_with_pdfplumber()
        except Exception as e:
            logger.warning(
                f"pdfplumber extraction failed: {e}. Falling back to pypdf..."
            )
            try:
                return self._extract_with_pypdf()
            except Exception as e2:
                logger.error(f"pypdf extraction also failed: {e2}")
                raise PDFExtractionError(
                    f"Failed to extract PDF with both methods. "
                    f"pdfplumber error: {e}, pypdf error: {e2}",
                    pdf_path=str(self.pdf_path),
                )

    def _extract_with_pdfplumber(self) -> Dict:
        """
        Extract text using pdfplumber (primary method).

        Returns:
            Dictionary with extracted data
        """
        logger.debug("Using pdfplumber for extraction")

        text_pages = []
        metadata = {}

        with pdfplumber.open(self.pdf_path) as pdf:
            # Extract metadata
            if pdf.metadata:
                metadata = {
                    "title": pdf.metadata.get("Title", ""),
                    "author": pdf.metadata.get("Author", ""),
                    "subject": pdf.metadata.get("Subject", ""),
                    "creator": pdf.metadata.get("Creator", ""),
                }

            # Extract text page by page
            for page_num, page in enumerate(pdf.pages, start=1):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        # Clean the text
                        page_text = self._clean_text(page_text)
                        text_pages.append(page_text)
                except Exception as e:
                    logger.warning(f"Failed to extract page {page_num}: {e}")
                    continue

        if not text_pages:
            raise PDFExtractionError(
                "No text could be extracted from PDF", pdf_path=str(self.pdf_path)
            )

        # Combine all pages
        full_text = "\n\n".join(text_pages)

        # Extract title from metadata or filename
        if not metadata.get("title"):
            metadata["title"] = self._guess_title_from_text(full_text) or self.pdf_path.stem

        return {
            "text": full_text,
            "metadata": metadata,
            "page_count": len(text_pages),
        }

    def _extract_with_pypdf(self) -> Dict:
        """
        Extract text using pypdf (fallback method).

        Returns:
            Dictionary with extracted data
        """
        logger.debug("Using pypdf for extraction")

        text_pages = []
        metadata = {}

        with open(self.pdf_path, "rb") as f:
            reader = pypdf.PdfReader(f)

            # Extract metadata
            if reader.metadata:
                metadata = {
                    "title": reader.metadata.get("/Title", ""),
                    "author": reader.metadata.get("/Author", ""),
                    "subject": reader.metadata.get("/Subject", ""),
                    "creator": reader.metadata.get("/Creator", ""),
                }

            # Extract text page by page
            for page_num, page in enumerate(reader.pages, start=1):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        page_text = self._clean_text(page_text)
                        text_pages.append(page_text)
                except Exception as e:
                    logger.warning(f"Failed to extract page {page_num}: {e}")
                    continue

        if not text_pages:
            raise PDFExtractionError(
                "No text could be extracted from PDF", pdf_path=str(self.pdf_path)
            )

        full_text = "\n\n".join(text_pages)

        # Extract title from metadata or filename
        if not metadata.get("title"):
            metadata["title"] = self._guess_title_from_text(full_text) or self.pdf_path.stem

        return {
            "text": full_text,
            "metadata": metadata,
            "page_count": len(text_pages),
        }

    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text
        """
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove excessive newlines
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def _guess_title_from_text(self, text: str) -> Optional[str]:
        """
        Try to guess the document title from the first lines of text.

        Args:
            text: Full document text

        Returns:
            Guessed title or None
        """
        lines = text.split("\n")
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            # Look for a line that's not too short and not too long
            if 10 < len(line) < 200:
                # Likely a title if it's in the first few lines and reasonably sized
                return line
        return None
