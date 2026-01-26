"""Main orchestrator for academic summary generation."""

from pathlib import Path
from typing import Optional

from ..api.openrouter_client import OpenRouterClient
from ..api.prompt_templates import build_summary_prompt
from ..config import Settings, get_settings
from ..utils.logger import get_logger
from .context_detector import ContextDetector
from .history_manager import HistoryManager
from .master_tracker import MasterTracker
from .output_formatter import OutputFormatter
from .pdf_extractor import PDFExtractor

logger = get_logger("summarizer")


class AcademicSummarizer:
    """Orchestrate the complete summary generation workflow."""

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize summarizer.

        Args:
            settings: Application settings (uses global settings if not provided)
        """
        self.settings = settings or get_settings()

    def generate_summary(
        self,
        pdf_path: Path,
        output_path: Optional[Path] = None,
        course_override: Optional[str] = None,
        week_override: Optional[str] = None,
        enable_history: Optional[bool] = None,
    ) -> Path:
        """
        Generate summary for a PDF reading with historical context.

        Args:
            pdf_path: Path to PDF file
            output_path: Optional output path (defaults to PDF's folder)
            course_override: Manual course code override
            week_override: Manual week override
            enable_history: Enable/disable historical context (uses settings if None)

        Returns:
            Path to generated summary file

        Raises:
            Various exceptions if workflow fails
        """
        pdf_path = Path(pdf_path).resolve()

        logger.info(f"Starting summary generation for: {pdf_path.name}")
        logger.info("=" * 60)

        # Determine if history should be used
        use_history = (
            enable_history if enable_history is not None else self.settings.enable_history
        )

        # Step 1: Extract PDF
        logger.info("Step 1/9: Extracting PDF text...")
        extractor = PDFExtractor(pdf_path)
        pdf_data = extractor.extract()
        logger.info(f"✓ Extracted {pdf_data['page_count']} pages")

        # Step 2: Detect context
        logger.info("Step 2/9: Detecting course context...")
        detector = ContextDetector(pdf_path)
        context = detector.detect_context(
            course_override=course_override, week_override=week_override
        )
        logger.info(
            f"✓ Course: {context['course_code']}, Week: {context['week']}, "
            f"Folder: {context['course_folder']}"
        )

        # Step 3-4: Get historical context (if enabled)
        previous_context = []
        if use_history and context["course_folder"]:
            logger.info("Step 3/9: Finding previous summaries...")
            history_mgr = HistoryManager(
                context["course_folder"], self.settings.max_previous_summaries
            )
            previous_summaries = history_mgr.find_previous_summaries()
            logger.info(f"✓ Found {len(previous_summaries)} previous summaries")

            if previous_summaries:
                logger.info("Step 4/9: Extracting context from previous summaries...")
                previous_context = history_mgr.extract_context_from_summaries(
                    previous_summaries
                )
                logger.info(f"✓ Extracted context from {len(previous_context)} summaries")
        else:
            if not use_history:
                logger.info("Step 3-4/9: Skipping historical context (disabled)")
            else:
                logger.info("Step 3-4/9: No course folder found, skipping history")

        # Step 5: Build enhanced prompt
        logger.info("Step 5/9: Building prompt with context...")
        prompt = build_summary_prompt(
            pdf_text=pdf_data["text"],
            context=context,
            previous_summaries=previous_context,
        )
        logger.info(f"✓ Prompt built ({len(prompt)} chars, ~{len(prompt)//4} tokens)")

        # Step 6: Call API
        logger.info("Step 6/9: Generating summary via OpenRouter API...")
        api_client = OpenRouterClient(self.settings)
        summary = api_client.generate_summary(prompt)
        logger.info(f"✓ Summary generated ({len(summary)} chars)")

        # Step 7: Format output
        logger.info("Step 7/9: Formatting output...")
        formatter = OutputFormatter()
        formatted = formatter.format_summary(
            summary, context, pdf_data["metadata"], len(previous_context)
        )
        logger.info("✓ Output formatted and validated")

        # Step 8: Save in same folder as PDF
        logger.info("Step 8/9: Saving summary file...")
        if not output_path:
            output_path = pdf_path.parent / f"{pdf_path.stem}_summary.md"

        output_path = Path(output_path).resolve()
        output_path.write_text(formatted, encoding="utf-8")
        logger.info(f"✓ Summary saved: {output_path}")

        # Step 9: Update master files (if enabled)
        if self.settings.auto_update_masters and context["course_code"]:
            logger.info("Step 9/9: Updating master files...")

            # Extract metadata for master files
            thesis = formatter.extract_thesis(summary)
            key_concepts = formatter.extract_key_concepts(summary)

            summary_metadata = {
                "week": context["week"],
                "title": pdf_data["metadata"].get("title", pdf_path.stem),
                "author": pdf_data["metadata"].get("author", "Unknown"),
                "thesis": thesis,
                "key_concepts": key_concepts,
                "summary_path": output_path,
                "date": datetime.now(),
            }

            tracker = MasterTracker(
                context["course_code"],
                context["course_folder"],
                self.settings.get_global_master_path(),
            )
            tracker.update_masters(summary_metadata)

            logger.info("✓ Master files updated")
            if tracker.course_master_path:
                logger.info(f"  - Course master: {tracker.course_master_path}")
            logger.info(f"  - Global master: {tracker.global_master_path}")
        else:
            logger.info("Step 9/9: Skipping master file updates (disabled)")

        logger.info("=" * 60)
        logger.info("✓ Summary generation completed successfully!")

        return output_path


# Import datetime for step 9
from datetime import datetime
