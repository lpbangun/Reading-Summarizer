# Academic Reading Summarizer

A CLI tool that generates structured 10-12 minute summaries from academic PDFs with **cumulative learning**—each summary automatically references concepts from previous weeks to build semester-long understanding.

## The Problem

Students read 50+ academic papers per semester. By week 10, connecting ideas across readings becomes overwhelming. Traditional note-taking doesn't scale.

## The Solution

Drop a PDF in your course folder. Get a structured summary that explicitly references your previous readings:

```
"Building on Week 3's concept of 'ritual efficacy' from Turner,
this week's reading extends the framework to digital spaces..."
```

The tool automatically:
1. Detects your course and week from folder structure
2. Finds and parses your previous summaries
3. Injects that context into the LLM prompt
4. Generates a summary with explicit cross-references
5. Updates master tracking files for quick review

## Output Structure

Each summary follows a 5-section template designed for seminar prep:

| Section | Time | Purpose |
|---------|------|---------|
| **I. Syllabus Contextualization** | 1-2 min | Course placement, themes, objectives |
| **II. Core Thesis & Architecture** | 3-4 min | Central argument, key terms, evidence, verbatim quotes |
| **III. Critical Tensions** | 2 min | Contradictions, counter-positions, assumptions |
| **IV. Cross-Reading Synthesis** | 3-4 min | Connections to previous weeks (the magic) |
| **V. Critical Questions** | 1-2 min | Socratic discussion prompts |

## Quick Start

```bash
# Clone and setup
git clone https://github.com/YOUR_USERNAME/academic-reading-summarizer.git
cd academic-reading-summarizer
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Add your OpenRouter API key to .env

# Generate a summary
python -m academic_summarizer path/to/PSYCH101/Week3/reading.pdf
```

**Output**: `reading_summary.md` saved next to the PDF, plus updated master files.

## Folder Structure

For automatic course/week detection:

```
courses/
├── PSYCH101/
│   ├── Week1/
│   │   ├── reading.pdf
│   │   └── reading_summary.md  # Generated
│   ├── Week2/
│   │   └── ...
│   └── PSYCH101_master.md      # Auto-updated index
```

## Configuration

Key settings in `.env`:

```bash
OPENROUTER_API_KEY=sk-or-v1-...   # Required
MODEL_NAME=x-ai/grok-4.1-fast     # Default model
ENABLE_HISTORY=true               # Cumulative learning on/off
MAX_PREVIOUS_SUMMARIES=10         # Cap history to control tokens
```

## How Cumulative Learning Works

1. **Week 1**: Standard summary, no history
2. **Week 2+**: Tool finds previous `*_summary.md` files, extracts thesis and key concepts, injects into prompt
3. **Section IV** explicitly requires the LLM to reference previous weeks

Token growth is modest (~5,300 tokens per historical week) and capped at 10 previous summaries.

## Requirements

- Python 3.9+
- [OpenRouter API key](https://openrouter.ai/) (uses Grok 4.1 Fast by default)

## Architecture

The codebase is designed for easy GUI migration—each component is stateless with clear I/O:

- `PDFExtractor` - Text extraction with fallback
- `ContextDetector` - Course/week detection from paths
- `HistoryManager` - Find and parse previous summaries
- `MasterTracker` - Update course and global index files

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

## License

MIT

---

*Summaries are study aids, not replacements. Always engage with the original texts.*
