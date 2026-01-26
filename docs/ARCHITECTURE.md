# Architecture Documentation

## System Overview

Academic Reading Summary CLI is a modular Python application designed for easy GUI migration. The architecture separates concerns into distinct layers:

```
┌─────────────────────────────────────────┐
│          CLI Layer (cli.py)             │  ← Replace with GUI
├─────────────────────────────────────────┤
│   Orchestration (summarizer.py)        │  ← Core workflow logic
├─────────────────────────────────────────┤
│  Core Components                         │
│  • pdf_extractor.py                     │
│  • context_detector.py                  │
│  • history_manager.py  (NEW!)           │
│  • master_tracker.py   (NEW!)           │
│  • output_formatter.py                  │
├─────────────────────────────────────────┤
│  API Integration                         │
│  • openrouter_client.py                 │
│  • prompt_templates.py                  │
├─────────────────────────────────────────┤
│  Configuration & Utils                   │
│  • config.py (Pydantic settings)        │
│  • logger.py, exceptions.py             │
└─────────────────────────────────────────┘
```

## Key Innovation: Cumulative Learning

The system's unique feature is **historical context integration**:

1. Before generating each summary, scan course folder for previous summaries
2. Extract key concepts and theses from past weeks
3. Inject this context into the API prompt
4. Generate summary with explicit connections to previous readings
5. Update master files for quick reference

## Component Details

### 1. Core Orchestrator (`core/summarizer.py`)

**Purpose**: Coordinates the 9-step workflow

**Key Method**: `generate_summary()`

```python
def generate_summary(
    pdf_path: Path,
    output_path: Optional[Path] = None,
    course_override: Optional[str] = None,
    week_override: Optional[str] = None,
    enable_history: Optional[bool] = None,
) -> Path:
    # 1. Extract PDF text
    # 2. Detect course context
    # 3. Find previous summaries
    # 4. Extract historical context
    # 5. Build prompt with history
    # 6. Call API
    # 7. Format output
    # 8. Save to file (same folder as PDF)
    # 9. Update master files
```

**GUI Integration Point**: Import and call `generate_summary()` from GUI, passing user-selected PDF path. Use callbacks for progress updates.

### 2. PDF Extractor (`core/pdf_extractor.py`)

**Purpose**: Extract text from PDFs with fallback strategies

**Strategy**:
- Primary: `pdfplumber` (better for academic PDFs with tables)
- Fallback: `pypdf` (simpler extraction)

**API**:
```python
class PDFExtractor:
    def extract(self) -> Dict:
        # Returns: {text: str, metadata: dict, page_count: int}
```

**GUI Considerations**:
- Can accept progress callbacks
- Should show page extraction progress
- Extraction takes 5-15 seconds for typical papers

### 3. Context Detector (`core/context_detector.py`)

**Purpose**: Parse folder structure to detect course, week, module

**Patterns Supported**:
- `PSYCH101/Week3/` → course="PSYCH101", week="3"
- `Sociology 200/Module 2/` → course="SOC200", module="2"

**API**:
```python
class ContextDetector:
    def detect_context(
        course_override: Optional[str] = None,
        week_override: Optional[str] = None
    ) -> Dict:
        # Returns: {course_code, course_folder, week, module, other_readings}
```

**GUI Considerations**:
- GUI can override detection with dropdown/input fields
- Show detected context to user before generating
- Identify course folder (critical for finding previous summaries)

### 4. History Manager (`core/history_manager.py`) **[NEW - CRITICAL]**

**Purpose**: Find and extract context from previous summaries

**Workflow**:
1. Scan course folder recursively for `*_summary.md` files
2. Parse YAML frontmatter for metadata
3. Extract thesis and key concepts from Section II
4. Return structured list of previous reading contexts

**API**:
```python
class HistoryManager:
    def find_previous_summaries(self) -> List[Path]:
        # Scans course folder, returns paths sorted chronologically

    def extract_context_from_summaries(self, summary_paths: List[Path]) -> List[Dict]:
        # Parses summaries, extracts: week, title, thesis, key_concepts
```

**GUI Considerations**:
- Show progress: "Loading previous summaries (3 of 10)..."
- Display preview of previous weeks before generating
- Allow user to toggle history on/off
- Cache extracted context for faster repeated runs

### 5. Master Tracker (`core/master_tracker.py`) **[NEW - CRITICAL]**

**Purpose**: Maintain per-course and global master files

**Master File Structure**:

**Course Master** (`PSYCH101_master.md`):
```markdown
# PSYCH101 - Course Learning History

### Week 1: Reading Title
- **Author**: Name
- **Core Thesis**: One-sentence thesis
- **Key Concepts**: concept1, concept2, concept3
- **Link**: [Title](Week1/reading_summary.md)
- **Date Generated**: 2026-01-20
```

**Global Master** (`_global_master.md`):
```markdown
# Academic Reading Master Index

## PSYCH101
- Week 1: [Title](path/to/summary.md) - Author

## SOC200
- Week 1: [Title](path/to/summary.md) - Author

---
*Last Updated*: 2026-01-25
*Total Courses*: 2
*Total Readings*: 5
```

**API**:
```python
class MasterTracker:
    def update_masters(self, summary_data: Dict) -> None:
        # Appends entry to both course and global masters
        # Updates statistics in footers
```

**GUI Considerations**:
- Display master files in dedicated viewer pane
- Make links clickable to open summaries
- Show timeline/progress visualization
- Allow export to PDF or Notion

### 6. OpenRouter Client (`api/openrouter_client.py`)

**Purpose**: Call OpenRouter API with Grok 4.1 Fast

**Features**:
- Automatic retry with exponential backoff
- Error handling (rate limits, timeouts, auth failures)
- Token usage logging

**API**:
```python
class OpenRouterClient:
    def generate_summary(self, prompt: str) -> str:
        # Calls OpenRouter API, returns summary text
```

**GUI Considerations**:
- API calls take 30-90 seconds
- Can implement streaming for real-time progress
- Show estimated cost before calling

### 7. Prompt Templates (`api/prompt_templates.py`)

**Purpose**: Build structured prompts with historical context

**Key Function**:
```python
def build_summary_prompt(
    pdf_text: str,
    context: Dict,
    previous_summaries: List[Dict] = None,
) -> str:
    # Injects previous weeks' context
    # Specifies exact 5-section output format
    # Returns complete prompt
```

**Prompt Structure**:
```
SYSTEM PROMPT: You are an expert academic reading assistant...

CONTEXT:
- Course: PSYCH101
- Week: 3

PREVIOUS WEEKS' LEARNING:
Week 1 - "Title" by Author
- Core Thesis: ...
- Key Concepts: ...

Week 2 - "Title" by Author
- Core Thesis: ...
- Key Concepts: ...

READING TEXT:
[PDF content]

OUTPUT REQUIREMENTS:
[Exact 5-section structure]
```

**GUI Considerations**:
- Show prompt preview before API call
- Allow users to edit/customize prompts
- Template variations for different disciplines

### 8. Output Formatter (`core/output_formatter.py`)

**Purpose**: Format and validate final markdown output

**Features**:
- Adds YAML frontmatter with metadata
- Validates all 5 sections present
- Adds header and footer
- Extracts thesis and key concepts for master files

**Output Structure**:
```markdown
---
title: "Reading Title"
author: "Author"
course: "PSYCH101"
week: 3
reading_time: "11-12 minutes"
previous_readings_referenced: 2
---

# Summary: Reading Title

## I. Syllabus Contextualization
...

## II. Core Thesis & Architecture
...

## III. Critical Tensions
...

## IV. Cross-Reading Synthesis
...

## V. Critical Questions
...

---
*Generated by Academic Summary CLI*
```

**GUI Considerations**:
- Display formatted preview before saving
- Allow user editing of generated summary
- Export options (PDF, DOCX, Notion)

### 9. Configuration (`config.py`)

**Purpose**: Centralized settings with validation

**Pydantic Settings**:
```python
class Settings(BaseSettings):
    openrouter_api_key: str
    model_name: str = "x-ai/grok-4.1-fast"
    temperature: float = 0.7
    max_tokens: int = 5000
    enable_history: bool = True
    max_previous_summaries: int = 10
    global_master_path: str = "~/.academic-summaries/_global_master.md"
```

**GUI Considerations**:
- Settings panel for all configurations
- Validate API key before saving
- Test connection button

## Data Flow

### Initial Summary (Week 1 - No History)

```
PDF File → PDFExtractor → {text, metadata}
                              ↓
                        ContextDetector → {course_code, week, course_folder}
                              ↓
                        PromptBuilder → prompt (no history)
                              ↓
                        OpenRouterClient → API response
                              ↓
                        OutputFormatter → formatted markdown
                              ↓
                        File System (save next to PDF)
                              ↓
                        MasterTracker → Create/update master files
```

### Later Summary (Week 3 - With History)

```
PDF File → PDFExtractor → {text, metadata}
                              ↓
                        ContextDetector → {course_code, week, course_folder}
                              ↓
                        HistoryManager → Find previous summaries
                              ↓ (Week 1 & 2 summaries)
                        HistoryManager → Extract context
                              ↓ (theses, key concepts)
                        PromptBuilder → prompt (WITH history)
                              ↓
                        OpenRouterClient → API response (references past weeks)
                              ↓
                        OutputFormatter → formatted markdown
                              ↓
                        File System (save next to PDF)
                              ↓
                        MasterTracker → Update master files (now 3 entries)
```

## State Management

### File System as State
- **Summaries**: `*_summary.md` files in reading folders
- **Course Masters**: `{COURSE}_master.md` in course root folders
- **Global Master**: `~/.academic-summaries/_global_master.md`

### No Database Required
- All state persists in markdown files
- Easy to version control, backup, and share
- Human-readable and editable

### Cache Opportunities (for GUI)
- Cache extracted PDF text (avoid re-extraction)
- Cache previous summary contexts (faster repeated runs)
- Cache course detection patterns (user corrections)

## Extension Points for GUI

### 1. Progress Callbacks
```python
# Example progress callback interface
def on_progress(step: str, progress: float, message: str):
    # Update GUI progress bar
    pass

# Modify components to accept callbacks
pdf_data = extractor.extract(progress_callback=on_progress)
```

### 2. Streaming API Responses
```python
# For real-time summary display
def generate_summary_streaming(prompt: str, callback: Callable):
    for chunk in api_client.stream(prompt):
        callback(chunk)  # Update GUI incrementally
```

### 3. Master File Viewer
- List all courses from global master
- Click course → show course master
- Click reading → open summary in editor
- Search across all summaries

### 4. Batch Processing
```python
def generate_summaries_batch(pdf_paths: List[Path]):
    for pdf_path in pdf_paths:
        yield summarizer.generate_summary(pdf_path)
        # GUI updates progress for each
```

### 5. Timeline Visualization
- Parse frontmatter from all summaries
- Display chronological timeline
- Show concept evolution across weeks

## Security Considerations

### API Key Storage
- **CLI**: `.env` file (never committed)
- **GUI**: OS keyring (e.g., `keyring` library)
```python
import keyring
keyring.set_password("academic-summarizer", "openrouter", api_key)
```

### Path Traversal Prevention
- All paths validated with `Path().resolve()`
- No user input directly used in file operations

### Safe Markdown Rendering
- If GUI renders markdown, sanitize to prevent XSS
- Use safe markdown parsers

## Performance Optimization

### Typical Timing (per summary)
- PDF extraction: 5-15 seconds
- Context detection: <1 second
- History scan: 1-3 seconds (grows with course size)
- History parsing: 2-15 seconds (depends on summary count)
- API call: 30-90 seconds
- Formatting: <1 second
- Master updates: 1-2 seconds
- **Total**: 40-130 seconds

### Optimization Strategies
1. **Cache PDF text**: Don't re-extract if PDF unchanged
2. **Cache history context**: Reuse for multiple summaries
3. **Parallel processing**: Generate summaries for multiple PDFs concurrently
4. **Lazy loading**: Only parse summaries when needed
5. **Incremental history**: Only parse new summaries, not all

### Token Management
- Week 1: ~22,500 tokens
- Week 10: ~33,000 tokens
- Stays within Grok's 128k limit
- Use `MAX_PREVIOUS_SUMMARIES=10` to cap growth

## Error Handling

### Exception Hierarchy
```
AcademicSummarizerError (base)
├── PDFExtractionError
├── ContextDetectionError
├── HistoryError
├── MasterFileError
├── APIError
└── ValidationError
```

### GUI Error Display
- User-friendly messages
- Actionable suggestions ("Check your API key in settings")
- Detailed logs available via "Show Details"

## Testing Strategy

### Unit Tests
- Each component tested independently
- Mock external dependencies (API, file system)

### Integration Tests
- End-to-end workflow with fixtures
- Test history system with multiple summaries
- Test master file updates

### Example Test
```python
def test_cumulative_learning():
    # Week 1
    summary1 = summarizer.generate_summary("week1.pdf")
    assert "Found 0 previous summaries" in logs

    # Week 2
    summary2 = summarizer.generate_summary("week2.pdf")
    assert "Found 1 previous summary" in logs
    assert "Week 1" in summary2.read_text()
```

## Future Enhancements

### Planned Features (Out of Scope for CLI)
1. **Cross-course synthesis**: Connect readings across different courses
2. **Concept graph**: Visualize connections between concepts
3. **Flashcard generation**: Auto-generate Anki cards from summaries
4. **Citation extraction**: Pull BibTeX from PDFs
5. **Collaborative features**: Share summaries with study groups

---

## Quick Reference: File Locations

| File | Purpose | Location |
|------|---------|----------|
| PDF Reading | Original academic paper | User's course folders |
| Summary | Generated summary | Same folder as PDF |
| Course Master | All readings for one course | Course root folder |
| Global Master | All readings, all courses | `~/.academic-summaries/` |
| Config | Settings and API key | `.env` in project root |
| Logs | Debug information | `./logs/app.log` |

For GUI migration specifics, see [GUI_MIGRATION_GUIDE.md](GUI_MIGRATION_GUIDE.md).
