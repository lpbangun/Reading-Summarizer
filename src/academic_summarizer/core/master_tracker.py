"""Manage master tracking files for courses."""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from ..utils.exceptions import MasterFileError
from ..utils.logger import get_logger

logger = get_logger("master_tracker")


class MasterTracker:
    """Maintain per-course and global master files."""

    def __init__(self, course_code: str, course_folder: Path, global_master_path: Path):
        """
        Initialize master tracker.

        Args:
            course_code: Course code (e.g., "PSYCH101")
            course_folder: Path to course root folder
            global_master_path: Path to global master file
        """
        self.course_code = course_code or "UNKNOWN"
        self.course_folder = Path(course_folder) if course_folder else None
        self.global_master_path = Path(global_master_path).expanduser()

        # Course master file path
        if self.course_folder:
            self.course_master_path = (
                self.course_folder / f"{self.course_code}_master.md"
            )
        else:
            self.course_master_path = None

    def update_masters(self, summary_data: Dict) -> None:
        """
        Update both course and global master files.

        Args:
            summary_data: Dictionary containing:
                - week: Week number or identifier
                - title: Reading title
                - author: Author name
                - thesis: Core thesis statement
                - key_concepts: List of key concepts
                - summary_path: Path to generated summary file
                - date: Generation date

        Raises:
            MasterFileError: If update fails
        """
        logger.info("Updating master files")

        try:
            # Update course-specific master
            if self.course_master_path:
                self._update_course_master(summary_data)

            # Update global master
            self._update_global_master(summary_data)

            logger.info("Master files updated successfully")

        except Exception as e:
            logger.error(f"Failed to update master files: {e}")
            raise MasterFileError(f"Failed to update master files: {e}")

    def _update_course_master(self, summary_data: Dict) -> None:
        """
        Update course-specific master file.

        Args:
            summary_data: Summary metadata
        """
        if not self.course_master_path:
            logger.warning("No course master path configured")
            return

        logger.debug(f"Updating course master: {self.course_master_path}")

        # Create master file if it doesn't exist
        if not self.course_master_path.exists():
            self._create_course_master()

        # Read existing content
        content = self.course_master_path.read_text(encoding="utf-8")

        # Create new entry
        new_entry = self._format_course_entry(summary_data)

        # Find insertion point (before the footer)
        footer_pattern = r"\n---\n\*Last Updated\*:"
        footer_match = re.search(footer_pattern, content)

        if footer_match:
            # Insert before footer
            insert_pos = footer_match.start()
            updated_content = content[:insert_pos] + "\n" + new_entry + "\n" + content[insert_pos:]
        else:
            # Append to end
            updated_content = content + "\n" + new_entry

        # Update footer
        updated_content = self._update_footer(updated_content)

        # Write back
        self.course_master_path.write_text(updated_content, encoding="utf-8")
        logger.debug(f"Course master updated: {self.course_master_path}")

    def _update_global_master(self, summary_data: Dict) -> None:
        """
        Update global master file.

        Args:
            summary_data: Summary metadata
        """
        logger.debug(f"Updating global master: {self.global_master_path}")

        # Create global master directory if needed
        self.global_master_path.parent.mkdir(parents=True, exist_ok=True)

        # Create master file if it doesn't exist
        if not self.global_master_path.exists():
            self._create_global_master()

        # Read existing content
        content = self.global_master_path.read_text(encoding="utf-8")

        # Find or create course section
        course_section_pattern = rf"##\s+{re.escape(self.course_code)}"
        course_match = re.search(course_section_pattern, content)

        new_entry = self._format_global_entry(summary_data)

        if course_match:
            # Course section exists, add entry to it
            # Find next section or footer
            next_section = re.search(r"\n##\s+[A-Z]", content[course_match.end():])
            footer = re.search(r"\n---\n", content[course_match.end():])

            if next_section:
                insert_pos = course_match.end() + next_section.start()
            elif footer:
                insert_pos = course_match.end() + footer.start()
            else:
                insert_pos = len(content)

            updated_content = (
                content[:insert_pos] + "\n" + new_entry + content[insert_pos:]
            )
        else:
            # Create new course section
            course_section = f"\n## {self.course_code}\n{new_entry}\n"

            # Insert before footer
            footer_match = re.search(r"\n---\n", content)
            if footer_match:
                insert_pos = footer_match.start()
                updated_content = (
                    content[:insert_pos] + course_section + content[insert_pos:]
                )
            else:
                updated_content = content + course_section

        # Update footer
        updated_content = self._update_global_footer(updated_content)

        # Write back
        self.global_master_path.write_text(updated_content, encoding="utf-8")
        logger.debug(f"Global master updated: {self.global_master_path}")

    def _create_course_master(self) -> None:
        """Create a new course master file."""
        logger.info(f"Creating new course master file: {self.course_master_path}")

        template = f"""# {self.course_code} - Course Learning History

*This file tracks all readings for {self.course_code}*

---
*Last Updated*: {datetime.now().strftime('%Y-%m-%d')}
*Total Readings*: 0
"""

        self.course_master_path.write_text(template, encoding="utf-8")

    def _create_global_master(self) -> None:
        """Create a new global master file."""
        logger.info(f"Creating new global master file: {self.global_master_path}")

        template = f"""# Academic Reading Master Index

*All courses and readings tracked here*

---
*Last Updated*: {datetime.now().strftime('%Y-%m-%d')}
*Total Courses*: 0
*Total Readings*: 0
"""

        self.global_master_path.write_text(template, encoding="utf-8")

    def _format_course_entry(self, summary_data: Dict) -> str:
        """
        Format entry for course master file.

        Args:
            summary_data: Summary metadata

        Returns:
            Formatted markdown entry
        """
        week = summary_data.get("week", "Unknown")
        title = summary_data.get("title", "Untitled")
        author = summary_data.get("author", "Unknown")
        thesis = summary_data.get("thesis", "")
        key_concepts = summary_data.get("key_concepts", [])
        summary_path = summary_data.get("summary_path")
        date = summary_data.get("date", datetime.now())

        # Make path relative to course folder
        if summary_path and self.course_folder:
            try:
                summary_path = Path(summary_path).relative_to(self.course_folder)
            except ValueError:
                summary_path = Path(summary_path).name

        # Format key concepts
        concepts_str = ", ".join(key_concepts[:7]) if key_concepts else "None extracted"

        entry = f"""### Week {week}: {title}
- **Author**: {author}
- **Core Thesis**: {thesis or "See full summary"}
- **Key Concepts**: {concepts_str}
- **Link**: [{title}]({summary_path})
- **Date Generated**: {date.strftime('%Y-%m-%d')}
"""

        return entry

    def _format_global_entry(self, summary_data: Dict) -> str:
        """
        Format entry for global master file.

        Args:
            summary_data: Summary metadata

        Returns:
            Formatted markdown entry
        """
        week = summary_data.get("week", "?")
        title = summary_data.get("title", "Untitled")
        author = summary_data.get("author", "Unknown")
        summary_path = summary_data.get("summary_path")

        # Format path for global master (absolute or relative to home)
        if summary_path:
            summary_path = Path(summary_path)

        entry = f"- Week {week}: [{title}]({summary_path}) - {author}"

        return entry

    def _update_footer(self, content: str) -> str:
        """
        Update footer statistics in course master.

        Args:
            content: File content

        Returns:
            Updated content
        """
        # Count readings (number of "### Week" headings)
        reading_count = len(re.findall(r"###\s+Week", content))

        # Update last updated date and count
        content = re.sub(
            r"\*Last Updated\*:.*",
            f"*Last Updated*: {datetime.now().strftime('%Y-%m-%d')}",
            content,
        )
        content = re.sub(
            r"\*Total Readings\*:.*",
            f"*Total Readings*: {reading_count}",
            content,
        )

        return content

    def _update_global_footer(self, content: str) -> str:
        """
        Update footer statistics in global master.

        Args:
            content: File content

        Returns:
            Updated content
        """
        # Count courses (number of "##" headings excluding main title)
        course_count = len(re.findall(r"\n##\s+[A-Z]", content))

        # Count total readings (number of "- Week" lines)
        reading_count = len(re.findall(r"^-\s+Week", content, re.MULTILINE))

        # Update footer
        content = re.sub(
            r"\*Last Updated\*:.*",
            f"*Last Updated*: {datetime.now().strftime('%Y-%m-%d')}",
            content,
        )
        content = re.sub(
            r"\*Total Courses\*:.*",
            f"*Total Courses*: {course_count}",
            content,
        )
        content = re.sub(
            r"\*Total Readings\*:.*",
            f"*Total Readings*: {reading_count}",
            content,
        )

        return content
