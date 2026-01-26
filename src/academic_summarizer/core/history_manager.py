"""Manage historical context from previous summaries."""

import re
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from ..utils.exceptions import HistoryError
from ..utils.logger import get_logger

logger = get_logger("history_manager")


class HistoryManager:
    """Find and extract context from previous summaries."""

    def __init__(self, course_folder: Path, max_summaries: int = 10):
        """
        Initialize history manager.

        Args:
            course_folder: Path to course root folder
            max_summaries: Maximum number of previous summaries to include
        """
        self.course_folder = Path(course_folder) if course_folder else None
        self.max_summaries = max_summaries

    def find_previous_summaries(self) -> List[Path]:
        """
        Find all previous summary files in the course folder.

        Returns:
            List of paths to summary files, sorted chronologically

        Raises:
            HistoryError: If course folder doesn't exist
        """
        if not self.course_folder:
            logger.debug("No course folder specified, no history available")
            return []

        if not self.course_folder.exists():
            logger.warning(f"Course folder doesn't exist: {self.course_folder}")
            return []

        logger.info(f"Searching for previous summaries in {self.course_folder}")

        summary_files = []

        try:
            # Recursively find all *_summary.md files
            for summary_path in self.course_folder.rglob("*_summary.md"):
                if summary_path.is_file():
                    summary_files.append(summary_path)

            # Sort by modification time (chronological order)
            summary_files.sort(key=lambda p: p.stat().st_mtime)

            logger.info(f"Found {len(summary_files)} previous summaries")

            # Limit to max_summaries (keep most recent)
            if len(summary_files) > self.max_summaries:
                logger.info(f"Limiting to {self.max_summaries} most recent summaries")
                summary_files = summary_files[-self.max_summaries :]

            return summary_files

        except Exception as e:
            logger.error(f"Error scanning for summaries: {e}")
            raise HistoryError(
                f"Failed to scan course folder for summaries: {e}",
                summary_path=str(self.course_folder),
            )

    def extract_context_from_summaries(
        self, summary_paths: List[Path]
    ) -> List[Dict]:
        """
        Extract context from previous summary files.

        Args:
            summary_paths: List of paths to summary files

        Returns:
            List of dictionaries with summary context:
            - week: Week number
            - title: Reading title
            - author: Author name
            - thesis: Core thesis statement
            - key_concepts: List of key concepts
        """
        if not summary_paths:
            return []

        logger.info(f"Extracting context from {len(summary_paths)} summaries")

        contexts = []

        for summary_path in summary_paths:
            try:
                context = self._parse_summary_file(summary_path)
                if context:
                    contexts.append(context)
            except Exception as e:
                logger.warning(f"Failed to parse {summary_path.name}: {e}")
                continue

        logger.info(f"Successfully extracted context from {len(contexts)} summaries")
        return contexts

    def _parse_summary_file(self, summary_path: Path) -> Optional[Dict]:
        """
        Parse a single summary file to extract context.

        Args:
            summary_path: Path to summary file

        Returns:
            Dictionary with context or None if parsing fails
        """
        try:
            content = summary_path.read_text(encoding="utf-8")

            # Extract YAML frontmatter
            frontmatter = self._extract_frontmatter(content)

            # Extract thesis from Section II
            thesis = self._extract_thesis(content)

            # Extract key concepts from Section II
            key_concepts = self._extract_key_concepts(content)

            context = {
                "week": frontmatter.get("week", "Unknown"),
                "title": frontmatter.get("title", summary_path.stem),
                "author": frontmatter.get("author", "Unknown"),
                "thesis": thesis,
                "key_concepts": key_concepts,
            }

            return context

        except Exception as e:
            logger.debug(f"Error parsing {summary_path.name}: {e}")
            return None

    def _extract_frontmatter(self, content: str) -> Dict:
        """
        Extract YAML frontmatter from markdown file.

        Args:
            content: File content

        Returns:
            Dictionary with frontmatter data
        """
        # Match YAML frontmatter between --- markers
        frontmatter_match = re.search(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)

        if frontmatter_match:
            yaml_content = frontmatter_match.group(1)
            try:
                return yaml.safe_load(yaml_content) or {}
            except yaml.YAMLError as e:
                logger.debug(f"Failed to parse frontmatter YAML: {e}")
                return {}

        return {}

    def _extract_thesis(self, content: str) -> str:
        """
        Extract core thesis from Section II.

        Args:
            content: File content

        Returns:
            Thesis statement or empty string
        """
        # Look for "Central argument" or "Central Argument" in Section II
        thesis_match = re.search(
            r"##\s*II\.\s*Core Thesis.*?[\n\r]+.*?[*-]\s*\*?\*?Central [Aa]rgument\*?\*?:?\s*(.+?)[\n\r]",
            content,
            re.DOTALL | re.IGNORECASE,
        )

        if thesis_match:
            thesis = thesis_match.group(1).strip()
            # Remove markdown formatting
            thesis = re.sub(r"\*\*|\*|__|_", "", thesis)
            return thesis

        return ""

    def _extract_key_concepts(self, content: str) -> List[str]:
        """
        Extract key concepts from Section II.

        Args:
            content: File content

        Returns:
            List of key concepts
        """
        concepts = []

        # Look for "Key Terms" section in Section II
        key_terms_match = re.search(
            r"##\s*II\.\s*Core Thesis.*?[\n\r]+.*?[*-]\s*\*?\*?Key [Tt]erms\*?\*?:?\s*(.+?)(?=[\n\r]\s*[*-]\s*\*?\*?[A-Z]|##\s*III\.)",
            content,
            re.DOTALL | re.IGNORECASE,
        )

        if key_terms_match:
            terms_text = key_terms_match.group(1)

            # Extract terms before colons or em dashes
            # Patterns like "ritualization: definition" or "embodiment - definition"
            term_matches = re.findall(
                r"([a-zA-Z][a-zA-Z\s]+?)(?::|–|-|—)\s*", terms_text
            )

            for term in term_matches:
                term = term.strip()
                if term and len(term) < 50:  # Reasonable term length
                    concepts.append(term)

        # Limit to first 7 concepts
        return concepts[:7]
