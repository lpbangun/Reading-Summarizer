"""Custom exceptions for the academic summarizer application."""


class AcademicSummarizerError(Exception):
    """Base exception for all application errors."""

    pass


class PDFExtractionError(AcademicSummarizerError):
    """Raised when PDF extraction fails."""

    def __init__(self, message: str, pdf_path: str = None):
        self.pdf_path = pdf_path
        super().__init__(message)


class ContextDetectionError(AcademicSummarizerError):
    """Raised when course context cannot be detected from folder structure."""

    def __init__(self, message: str, path: str = None):
        self.path = path
        super().__init__(message)


class HistoryError(AcademicSummarizerError):
    """Raised when there's an error accessing or parsing previous summaries."""

    def __init__(self, message: str, summary_path: str = None):
        self.summary_path = summary_path
        super().__init__(message)


class MasterFileError(AcademicSummarizerError):
    """Raised when there's an error creating or updating master files."""

    def __init__(self, message: str, master_path: str = None):
        self.master_path = master_path
        super().__init__(message)


class APIError(AcademicSummarizerError):
    """Raised when OpenRouter API fails."""

    def __init__(self, message: str, status_code: int = None, response: str = None):
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class ValidationError(AcademicSummarizerError):
    """Raised when output validation fails."""

    def __init__(self, message: str, missing_sections: list = None):
        self.missing_sections = missing_sections or []
        super().__init__(message)


class OCRError(PDFExtractionError):
    """Raised when OCR extraction fails."""

    pass


class ConfigurationError(AcademicSummarizerError):
    """Raised when there's a configuration error."""

    pass
