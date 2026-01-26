# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Academic Reading Summary CLI - generates structured 10-12 minute summaries from academic PDFs with **cumulative learning**: each summary references concepts from previous weeks to build semester-long understanding.

**Core Innovation**: Historical context system that automatically finds previous summaries, extracts thesis/concepts, and injects them into prompts so the LLM makes explicit connections (e.g., "Building on Week 1's concept of X...").

## Development Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .

# Configure API key
cp .env.example .env
# Edit .env and add your OpenRouter API key
```

### Running the CLI
```bash
# Basic usage (from project root)
python -m academic_summarizer path/to/reading.pdf --course PSYCH101 --week 3

# Interactive mode (Windows batch script)
cd "C:\Users\logsa\OneDrive\Documents\Spring 2026"
summarize-here.bat
```

### Testing
```bash
# Run all tests with coverage
pytest tests/ -v --cov=src/academic_summarizer

# Run specific test file
pytest tests/test_summarizer.py -v

# Type checking
mypy src/academic_summarizer

# Code formatting
black src/ tests/
```

## Architecture: The 9-Step Pipeline

The `AcademicSummarizer.generate_summary()` method in `core/summarizer.py` orchestrates:

1. **PDF Extraction** (`core/pdf_extractor.py`) - pdfplumber → pypdf fallback
2. **Context Detection** (`core/context_detector.py`) - Regex-based folder parsing for course code, week number
3. **Find Previous Summaries** (`core/history_manager.py`) - Scan course folder for `*_summary.md` files
4. **Extract Historical Context** - Parse YAML frontmatter + Section II (thesis, key concepts) from each previous summary
5. **Build Prompt** (`api/prompt_templates.py`) - Inject history into "PREVIOUS WEEKS' LEARNING" section
6. **Call API** (`api/openrouter_client.py`) - OpenRouter with Grok 4.1 Fast, 3-attempt exponential backoff
7. **Format Output** (`core/output_formatter.py`) - Add YAML frontmatter, validate 5 sections
8. **Save Summary** - Write to same folder as PDF: `{filename}_summary.md`
9. **Update Master Files** (`core/master_tracker.py`) - Append to course master + global master

## Key Design Patterns

### Stateless Components
Each module is independently instantiable with clear I/O:
- `PDFExtractor(path).extract()` → `{text, metadata, page_count}`
- `ContextDetector(path).detect_context()` → `{course_code, week, course_folder, ...}`
- `HistoryManager(folder).find_previous_summaries()` + `.extract_context_from_summaries(paths)`

**Why**: Enables easy GUI migration - just call methods from UI event handlers.

### File System as State Database
No database. State persists in three markdown files:
- **Summary files** (`*_summary.md`) - Individual readings with YAML frontmatter
- **Course master** (`{COURSE_CODE}_master.md`) - Per-course index with thesis + concepts for each week
- **Global master** (`~/.academic-summaries/_global_master.md`) - Cross-course index

**Benefit**: Hand-editable, version-controllable, shareable, no lock-in.

### Progressive Enhancement with History
Prompt template has two modes:
- **Week 1** (no previous summaries): Generic prompt
- **Week 2+**: Enhanced prompt includes "PREVIOUS WEEKS' LEARNING" section with thesis/concepts from earlier weeks

**Detection**: Automatic based on `HistoryManager.find_previous_summaries()` results.

### Context Detection via Folder Parsing
Regex patterns in `core/context_detector.py`:
- Course codes: `[A-Z]{3,4}\d{3,4}` (handles `PSYCH101`, `PSYCH 101`, `Psych101`)
- Week numbers: `week[-_\s]?(\d+)` (handles `Week3`, `Week 3`, `week-3`)

**Fallback**: Traverses parent folders if course code not found at PDF level.

## Critical Workflows

### First Reading (Week 1 - No History)
```
PDF → Extract (5-15s) → Detect context (1s) →
Find summaries (0 results) →
Build prompt WITHOUT history →
API call (30-90s) →
Format → Save →
CREATE course master + global master
```
**Output**: 3 files created, ~22,500 tokens used

### Later Reading (Week 3 - With History)
```
PDF → Extract → Detect context →
Scan folder (finds Week 1-2 summaries) →
Parse summaries (extract thesis, concepts) →
Build prompt WITH history (+5,300 tokens) →
API call (30-90s) →
Format → Save →
APPEND to course master + global master
```
**Output**: 1 file created, 2 files updated, ~27,800 tokens used

### Token Growth Over Semester
- Week 1: ~22,500 tokens
- Week 5: ~27,800 tokens
- Week 10: ~33,000 tokens (capped by `MAX_PREVIOUS_SUMMARIES=10`)
- All within Grok's 128k context window

## Configuration System

Uses Pydantic BaseSettings in `config.py`. Key settings from `.env`:

**Required**:
- `OPENROUTER_API_KEY` - Must start with "sk-or-"

**API Parameters**:
- `MODEL_NAME` (default: `x-ai/grok-4.1-fast`)
- `TEMPERATURE` (default: 0.7)
- `MAX_TOKENS` (default: 5000)

**Historical Context**:
- `ENABLE_HISTORY` (default: true) - Toggle cumulative learning
- `MAX_PREVIOUS_SUMMARIES` (default: 10) - Cap history growth to control token usage

**Master Files**:
- `GLOBAL_MASTER_PATH` (default: `~/.academic-summaries/_global_master.md`)

## Cumulative Learning System (Core Innovation)

### How It Works

**HistoryManager** (`core/history_manager.py`):
1. Recursively scans course folder for `*_summary.md` files
2. Sorts chronologically by modification time
3. Parses each summary:
   - YAML frontmatter → week, title, author
   - Section II → extracts "Central Argument" via regex
   - Section II → extracts up to 7 "Key Terms"
4. Returns list of dicts: `{week, title, author, thesis, key_concepts}`
5. Limits to `MAX_PREVIOUS_SUMMARIES` most recent

**Prompt Injection** (`api/prompt_templates.py`):
- Builds "PREVIOUS WEEKS' LEARNING:" section
- For each previous week: thesis + top 5 concepts
- Section IV instructions explicitly require: "Reference specific weeks and show how this reading builds upon, challenges, or extends them"

**Result**: LLM sees context like:
```
Week 1 - "Author X" argued Y
Week 2 - "Author Z" showed W
Current reading: [explain how it relates to X and Z]
```

### Cost Trade-off
History adds ~5,300 tokens per summary after Week 1. Total semester cost predictable and within Grok's limits.

## Important Implementation Details

### PDF Extraction Fallback Strategy
```python
try:
    return self._extract_with_pdfplumber()  # Primary (handles tables)
except Exception:
    return self._extract_with_pypdf()      # Fallback (more reliable for plain text)
```

### Master File Update Logic
`MasterTracker.update_masters()`:
1. Check if course master exists; create from template if not
2. Read existing content
3. Find footer separator (`---\n*Last Updated*:`)
4. Insert new entry **before** footer
5. Update footer stats (count `### Week` entries)
6. Repeat for global master (uses course sections `## COURSE_CODE`)

**Atomic writes**: Uses temp file + move to prevent corruption.

### Error Recovery
- **PDF extraction**: Auto-fallback to pypdf on failure
- **Context detection**: Traverses parent folders
- **History parsing**: Skips unparseable summaries with warnings, continues anyway
- **API calls**: 3 retries with exponential backoff (tenacity library)

## Extending the System

### For GUI Development
The CLI is just a thin wrapper. To build a GUI:
1. Import `AcademicSummarizer` from `core/summarizer.py`
2. Call `generate_summary(pdf_path)` from button click handler
3. Add progress callbacks (architecture supports it - see ARCHITECTURE.md)
4. Display master files in sidebar navigator
5. Show generated summaries in rich text widget

**Key insight**: All state is in markdown files, so GUI can just read/write them directly.

### Adding New Prompt Sections
Edit `api/prompt_templates.py`:
1. Update `build_summary_prompt()` to add section to template
2. Update `OutputFormatter.REQUIRED_SECTIONS` to validate presence
3. Sections must match exact markdown headers: `## {ROMAN}. {Title}`

### Custom Context Detectors
Subclass `ContextDetector` and override `detect_context()`:
```python
class CustomDetector(ContextDetector):
    def detect_context(self) -> dict:
        # Your custom logic
        return {"course_code": ..., "week": ..., ...}
```

## Common Issues

### "Course code not detected"
- Check folder structure matches patterns: `COURSE101/Week3/`
- Or use CLI override: `--course PSYCH101 --week 3`

### "No previous summaries found" (when they exist)
- Ensure summaries are named `*_summary.md`
- Check they're in the same course folder tree
- Verify YAML frontmatter is valid (use `---` delimiters)

### API timeout or rate limits
- Increase `REQUEST_TIMEOUT` in `.env`
- For rate limits: wait and retry (automatic with tenacity)

### Unicode errors on Windows
- Known issue with Rich library's checkmarks in cp1252 encoding
- Cosmetic only - doesn't affect functionality
- Avoid using `--verbose` flag to hide

## File Organization

Summaries saved **in same folder as PDF**:
```
Spring 2026/
├── PSYCH101/
│   ├── Week1/
│   │   ├── reading1.pdf
│   │   └── reading1_summary.md  ← Generated here
│   ├── Week2/
│   │   ├── reading2.pdf
│   │   └── reading2_summary.md
│   └── PSYCH101_master.md       ← Course index
└── _global_master.md             ← (optional, can be in ~/.academic-summaries/)
```

**Naming convention**: `{original_filename}_summary.md` (preserves original name for easy reference)
