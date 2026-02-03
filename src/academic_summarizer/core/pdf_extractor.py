"""PDF text extraction with pdfplumber, pypdf, and OCR fallback."""

import re
from pathlib import Path
from typing import Dict, Optional

import pdfplumber
import pypdf
import pypdfium2

from ..config import get_settings
from ..utils.exceptions import PDFExtractionError, OCRError
from ..utils.logger import get_logger

# Lazy import pytesseract to avoid errors if Tesseract isn't installed
pytesseract = None

logger = get_logger("pdf_extractor")


def _get_pytesseract():
    """Lazy load pytesseract and configure Tesseract path."""
    global pytesseract
    if pytesseract is None:
        import pytesseract as _pytesseract
        pytesseract = _pytesseract

        # Configure Tesseract path if specified in settings
        settings = get_settings()
        if settings.tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_path
        else:
            # Common Windows default path
            default_path = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
            if default_path.exists():
                pytesseract.pytesseract.tesseract_cmd = str(default_path)

    return pytesseract


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
            PDFExtractionError: If extraction fails with all methods
        """
        logger.info(f"Extracting text from {self.pdf_path.name}")

        # Try pdfplumber first (handles tables and complex layouts)
        try:
            result = self._extract_with_pdfplumber()
            if result.get("text", "").strip():
                return result
            logger.warning("pdfplumber returned empty text, trying pypdf...")
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}. Falling back to pypdf...")

        # Try pypdf as second option
        try:
            result = self._extract_with_pypdf()
            if result.get("text", "").strip():
                return result
            logger.warning("pypdf returned empty text, trying OCR...")
        except Exception as e2:
            logger.warning(f"pypdf extraction also failed: {e2}")

        # Try OCR as final fallback (for scanned PDFs)
        settings = get_settings()
        if settings.enable_ocr:
            try:
                logger.info("Attempting OCR extraction for scanned PDF...")
                return self._extract_with_ocr()
            except Exception as e3:
                logger.error(f"OCR extraction failed: {e3}")
                raise PDFExtractionError(
                    f"Failed to extract PDF with all methods (pdfplumber, pypdf, OCR). "
                    f"This may be a corrupted or protected PDF. OCR error: {e3}",
                    pdf_path=str(self.pdf_path),
                )
        else:
            raise PDFExtractionError(
                "No text could be extracted from PDF. This appears to be a scanned PDF. "
                "Enable OCR in settings (ENABLE_OCR=true) and install Tesseract to process it.",
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

    def _extract_with_ocr(self) -> Dict:
        """
        Extract text using OCR (fallback for scanned PDFs).

        Uses pypdfium2 to render PDF pages to images, then pytesseract for OCR.

        Returns:
            Dictionary with extracted data

        Raises:
            OCRError: If OCR extraction fails
        """
        logger.debug("Using OCR for extraction")

        tesseract = _get_pytesseract()
        settings = get_settings()

        text_pages = []
        metadata = {"title": "", "author": "", "subject": "", "creator": ""}

        try:
            # Open PDF with pypdfium2
            pdf = pypdfium2.PdfDocument(str(self.pdf_path))

            for page_num in range(len(pdf)):
                try:
                    # Render page to image (300 DPI for good OCR quality)
                    page = pdf[page_num]
                    bitmap = page.render(scale=300 / 72)  # 300 DPI
                    pil_image = bitmap.to_pil()

                    # Run OCR on the image
                    page_text = tesseract.image_to_string(
                        pil_image, lang=settings.ocr_language
                    )

                    if page_text:
                        page_text = self._clean_text(page_text)
                        text_pages.append(page_text)

                    logger.debug(f"OCR completed for page {page_num + 1}")

                except Exception as e:
                    logger.warning(f"OCR failed for page {page_num + 1}: {e}")
                    continue

            pdf.close()

        except Exception as e:
            raise OCRError(
                f"OCR extraction failed: {e}. "
                "Make sure Tesseract is installed and TESSERACT_PATH is set correctly.",
                pdf_path=str(self.pdf_path),
            )

        if not text_pages:
            raise OCRError(
                "OCR could not extract any text from PDF",
                pdf_path=str(self.pdf_path),
            )

        full_text = "\n\n".join(text_pages)

        # Extract title from text or use filename
        metadata["title"] = self._guess_title_from_text(full_text) or self.pdf_path.stem

        logger.info(f"OCR extracted {len(text_pages)} pages successfully")

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
