"""Course context detection from folder structure."""

import re
from pathlib import Path
from typing import Dict, List, Optional

from ..utils.exceptions import ContextDetectionError
from ..utils.logger import get_logger

logger = get_logger("context_detector")


class ContextDetector:
    """Detect course context from folder structure and filenames."""

    # Regex patterns for detection
    COURSE_CODE_PATTERN = re.compile(r"([A-Z]{3,4})\s?(\d{3,4})", re.IGNORECASE)
    WEEK_PATTERN = re.compile(r"week[-_\s]?(\d+)", re.IGNORECASE)
    MODULE_PATTERN = re.compile(r"(module|unit|section)[-_\s]?(\d+)", re.IGNORECASE)

    def __init__(self, pdf_path: Path):
        """
        Initialize context detector.

        Args:
            pdf_path: Path to PDF file
        """
        self.pdf_path = Path(pdf_path).resolve()

    def detect_context(
        self, course_override: Optional[str] = None, week_override: Optional[str] = None
    ) -> Dict:
        """
        Detect course context from folder structure.

        Args:
            course_override: Manual course code override
            week_override: Manual week override

        Returns:
            Dictionary with context information:
            - course_code: Course code (e.g., "PSYCH101")
            - course_name: Full course name (extracted or same as code)
            - course_folder: Path to course root folder
            - week: Week number or identifier
            - module: Module name if detected
            - other_readings: List of other PDFs in same folder
        """
        logger.info(f"Detecting context for {self.pdf_path.name}")

        context = {
            "course_code": None,
            "course_name": None,
            "course_folder": None,
            "week": None,
            "module": None,
            "other_readings": [],
        }

        # Use overrides if provided
        if course_override:
            context["course_code"] = course_override
            context["course_name"] = course_override
            logger.info(f"Using manual course override: {course_override}")

        if week_override:
            context["week"] = week_override
            logger.info(f"Using manual week override: {week_override}")

        # Parse folder structure
        parts = self.pdf_path.parts

        # Traverse from file up to find course code and week
        for i, part in enumerate(reversed(parts)):
            # Skip the filename itself
            if i == 0:
                continue

            # Try to extract course code
            if not context["course_code"]:
                course_match = self.COURSE_CODE_PATTERN.search(part)
                if course_match:
                    context["course_code"] = f"{course_match.group(1)}{course_match.group(2)}"
                    context["course_name"] = part  # Use full folder name
                    # Course folder is this level
                    context["course_folder"] = Path(*parts[: len(parts) - i])
                    logger.debug(f"Detected course: {context['course_code']}")

            # Try to extract week/module
            if not context["week"]:
                week_match = self.WEEK_PATTERN.search(part)
                if week_match:
                    context["week"] = week_match.group(1)
                    logger.debug(f"Detected week: {context['week']}")

            # Try to extract module
            if not context["module"]:
                module_match = self.MODULE_PATTERN.search(part)
                if module_match:
                    context["module"] = f"{module_match.group(1).title()} {module_match.group(2)}"
                    logger.debug(f"Detected module: {context['module']}")

            # If we have both course and week, we can stop
            if context["course_code"] and context["week"]:
                break

        # If course folder not yet identified, try to find it by looking for course code
        if not context["course_folder"] and context["course_code"]:
            context["course_folder"] = self._find_course_folder(context["course_code"])

        # If still no course folder, use parent directory of PDF
        if not context["course_folder"]:
            # Try using grandparent or great-grandparent as course folder
            if len(parts) >= 3:
                context["course_folder"] = self.pdf_path.parent.parent
            else:
                context["course_folder"] = self.pdf_path.parent

        # Find other readings in the same folder
        context["other_readings"] = self._find_sibling_readings()

        # Log detection results
        if not context["course_code"]:
            logger.warning(
                "Could not detect course code from folder structure. "
                "Use --course flag to specify manually."
            )

        if not context["week"]:
            logger.warning(
                "Could not detect week from folder structure. "
                "Use --week flag to specify manually."
            )

        logger.info(
            f"Context detected - Course: {context['course_code']}, "
            f"Week: {context['week']}, "
            f"Course folder: {context['course_folder']}"
        )

        return context

    def _find_course_folder(self, course_code: str) -> Optional[Path]:
        """
        Find the course root folder by looking for folder containing course code.

        Args:
            course_code: Course code to search for

        Returns:
            Path to course folder or None
        """
        current = self.pdf_path.parent

        # Traverse up the directory tree
        for _ in range(5):  # Look up to 5 levels
            if course_code.upper() in current.name.upper():
                return current
            if current.parent == current:  # Reached root
                break
            current = current.parent

        return None

    def _find_sibling_readings(self) -> List[str]:
        """
        Find other PDF files in the same directory.

        Returns:
            List of PDF filenames (excluding current file)
        """
        sibling_pdfs = []

        try:
            for pdf_file in self.pdf_path.parent.glob("*.pdf"):
                if pdf_file != self.pdf_path:
                    # Use just the filename without extension
                    sibling_pdfs.append(pdf_file.stem)
        except Exception as e:
            logger.warning(f"Failed to scan for sibling PDFs: {e}")

        if sibling_pdfs:
            logger.debug(f"Found {len(sibling_pdfs)} other readings in folder")

        return sibling_pdfs
