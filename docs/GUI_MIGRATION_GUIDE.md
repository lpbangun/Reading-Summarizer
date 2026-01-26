# GUI Migration Guide

This guide explains how to wrap the Academic Reading Summary CLI with a graphical user interface. The CLI was designed with GUI migration in mind, using clean separation of concerns.

## Architecture for GUI

### Core Principle: Separate Presentation from Logic

```
┌─────────────────────────────────┐
│      GUI Layer (New)            │ ← Flask/PyQt/Electron
│  • File selection               │
│  • Progress display             │
│  • Settings management          │
│  • Master file viewer           │
└─────────────────────────────────┘
              ↓ (imports)
┌─────────────────────────────────┐
│   Core Logic (Existing)         │ ← NO CHANGES NEEDED
│  • PDFExtractor                 │
│  • HistoryManager               │
│  • OpenRouterClient             │
│  • MasterTracker                │
└─────────────────────────────────┘
```

**Key Insight**: The `core/` and `api/` modules have **zero CLI dependencies**. They can be imported directly into your GUI application.

## Recommended GUI Frameworks

### Option 1: Web-Based GUI (Flask + React)

**Pros**:
- Modern, responsive UI
- Easy deployment (run locally or on server)
- Rich component libraries
- Cross-platform

**Cons**:
- Requires web development knowledge
- More complex setup

### Option 2: Desktop GUI (PyQt6/PySide6)

**Pros**:
- Native desktop application
- Rich Qt widgets
- Excellent documentation
- Single executable possible

**Cons**:
- Steeper learning curve
- Platform-specific packaging

### Option 3: Simple Desktop GUI (Tkinter)

**Pros**:
- Built into Python
- Simple to learn
- Lightweight

**Cons**:
- Less modern appearance
- Limited widgets

## Implementation Examples

### Example 1: Flask Web GUI

```python
# app.py
from flask import Flask, render_template, request, jsonify
from pathlib import Path
from academic_summarizer.core.summarizer import AcademicSummarizer
from academic_summarizer.config import get_settings

app = Flask(__name__)
summarizer = AcademicSummarizer(get_settings())

@app.route('/')
def index():
    """Render main page"""
    return render_template('index.html')

@app.route('/api/summarize', methods=['POST'])
def summarize():
    """Generate summary endpoint"""
    data = request.json
    pdf_path = Path(data['pdf_path'])

    try:
        # Call core logic directly
        output_path = summarizer.generate_summary(
            pdf_path=pdf_path,
            course_override=data.get('course'),
            week_override=data.get('week'),
            enable_history=data.get('enable_history', True)
        )

        return jsonify({
            'success': True,
            'output_path': str(output_path),
            'message': 'Summary generated successfully'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/courses', methods=['GET'])
def get_courses():
    """List all courses from global master"""
    settings = get_settings()
    global_master = settings.get_global_master_path()

    if not global_master.exists():
        return jsonify({'courses': []})

    # Parse global master to extract course list
    content = global_master.read_text(encoding='utf-8')
    courses = []
    # ... parsing logic ...

    return jsonify({'courses': courses})

if __name__ == '__main__':
    app.run(debug=True)
```

**Frontend (React)**:
```jsx
// components/Summarizer.jsx
import React, { useState } from 'react';

function Summarizer() {
    const [pdfPath, setPdfPath] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);

        try {
            const response = await fetch('/api/summarize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pdf_path: pdfPath })
            });

            const data = await response.json();
            setResult(data);
        } catch (error) {
            console.error('Error:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="summarizer">
            <h1>Academic Summary Generator</h1>
            <form onSubmit={handleSubmit}>
                <input
                    type="file"
                    accept=".pdf"
                    onChange={(e) => setPdfPath(e.target.files[0].path)}
                />
                <button type="submit" disabled={loading}>
                    {loading ? 'Generating...' : 'Generate Summary'}
                </button>
            </form>
            {result && (
                <div className="result">
                    {result.success ? (
                        <p>Summary saved to: {result.output_path}</p>
                    ) : (
                        <p className="error">{result.error}</p>
                    )}
                </div>
            )}
        </div>
    );
}
```

### Example 2: PyQt6 Desktop GUI

```python
# gui_main.py
import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QLabel, QFileDialog, QProgressBar,
    QTextEdit, QCheckBox
)
from PyQt6.QtCore import QThread, pyqtSignal

from academic_summarizer.core.summarizer import AcademicSummarizer
from academic_summarizer.config import get_settings


class SummarizerThread(QThread):
    """Background thread for summary generation"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, pdf_path, enable_history=True):
        super().__init__()
        self.pdf_path = pdf_path
        self.enable_history = enable_history

    def run(self):
        try:
            self.progress.emit("Starting summary generation...")
            summarizer = AcademicSummarizer(get_settings())

            output_path = summarizer.generate_summary(
                pdf_path=self.pdf_path,
                enable_history=self.enable_history
            )

            self.finished.emit(str(output_path))

        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Academic Summary Generator")
        self.setGeometry(100, 100, 800, 600)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # File selection
        self.file_label = QLabel("No file selected")
        layout.addWidget(self.file_label)

        select_btn = QPushButton("Select PDF")
        select_btn.clicked.connect(self.select_file)
        layout.addWidget(select_btn)

        # Options
        self.history_checkbox = QCheckBox("Enable historical context")
        self.history_checkbox.setChecked(True)
        layout.addWidget(self.history_checkbox)

        # Generate button
        self.generate_btn = QPushButton("Generate Summary")
        self.generate_btn.clicked.connect(self.generate_summary)
        self.generate_btn.setEnabled(False)
        layout.addWidget(self.generate_btn)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status text
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        layout.addWidget(self.status_text)

        self.pdf_path = None
        self.thread = None

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF", "", "PDF Files (*.pdf)"
        )
        if file_path:
            self.pdf_path = Path(file_path)
            self.file_label.setText(f"Selected: {self.pdf_path.name}")
            self.generate_btn.setEnabled(True)

    def generate_summary(self):
        if not self.pdf_path:
            return

        # Disable button during generation
        self.generate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        # Start background thread
        self.thread = SummarizerThread(
            self.pdf_path,
            self.history_checkbox.isChecked()
        )
        self.thread.progress.connect(self.update_status)
        self.thread.finished.connect(self.on_finished)
        self.thread.error.connect(self.on_error)
        self.thread.start()

    def update_status(self, message):
        self.status_text.append(message)

    def on_finished(self, output_path):
        self.progress_bar.setVisible(False)
        self.generate_btn.setEnabled(True)
        self.status_text.append(f"\n✓ Summary saved to: {output_path}")

    def on_error(self, error_message):
        self.progress_bar.setVisible(False)
        self.generate_btn.setEnabled(True)
        self.status_text.append(f"\n✗ Error: {error_message}")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
```

## Key Integration Points

### 1. File Selection

**CLI**:
```python
click.argument('pdf_path', type=click.Path(exists=True))
```

**GUI**:
```python
# PyQt
file_path, _ = QFileDialog.getOpenFileName(
    self, "Select PDF", "", "PDF Files (*.pdf)"
)

# Web (use <input type="file" accept=".pdf">)
```

### 2. Progress Feedback

**CLI**: Rich progress bars

**GUI**: Multiple approaches

**A) Callback-based** (requires modifying core):
```python
def extract_with_progress(self, callback):
    with pdfplumber.open(self.pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            callback(f"Extracting page {i+1}/{len(pdf.pages)}")
```

**B) Threading + signals** (no core changes):
```python
# Run in background thread, emit signals
class WorkerThread(QThread):
    progress = pyqtSignal(str)

    def run(self):
        self.progress.emit("Step 1/9...")
        # Call core logic
        self.progress.emit("Step 2/9...")
```

**C) Logging interception** (clever approach):
```python
# Intercept log messages for progress updates
class GUILogHandler(logging.Handler):
    def emit(self, record):
        # Parse log messages and update GUI
        if "Step X/9" in record.getMessage():
            gui.update_progress(...)
```

### 3. Settings Management

**CLI**: `.env` file

**GUI**: Settings dialog + OS keyring

```python
import keyring
from PyQt6.QtWidgets import QDialog, QLineEdit

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")

        # API Key input (masked)
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)

        # Load from keyring
        saved_key = keyring.get_password(
            "academic-summarizer", "openrouter"
        )
        if saved_key:
            self.api_key_input.setText(saved_key)

    def save_settings(self):
        # Save to keyring
        keyring.set_password(
            "academic-summarizer",
            "openrouter",
            self.api_key_input.text()
        )
```

### 4. Master File Viewer

**Key Feature**: Browse all readings from GUI

```python
class MasterFileViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.load_global_master()

    def load_global_master(self):
        """Parse and display global master"""
        settings = get_settings()
        global_master = settings.get_global_master_path()

        if not global_master.exists():
            return

        content = global_master.read_text(encoding='utf-8')

        # Parse markdown to extract courses and readings
        # Display in tree view with clickable links
        # Click → open summary in viewer
```

### 5. Historical Context Preview

**Feature**: Show previous readings before generating

```python
from academic_summarizer.core.history_manager import HistoryManager

def preview_context(course_folder):
    """Show what historical context will be used"""
    history_mgr = HistoryManager(course_folder, max_summaries=10)
    previous_summaries = history_mgr.find_previous_summaries()
    previous_context = history_mgr.extract_context_from_summaries(
        previous_summaries
    )

    # Display in GUI:
    # "This summary will reference X previous readings:"
    # - Week 1: "Title" by Author (key concepts: ...)
    # - Week 2: "Title" by Author (key concepts: ...)
```

## Advanced Features for GUI

### 1. Batch Processing

```python
def batch_generate(pdf_paths, progress_callback):
    """Generate summaries for multiple PDFs"""
    summarizer = AcademicSummarizer(get_settings())

    for i, pdf_path in enumerate(pdf_paths):
        progress_callback(f"Processing {i+1}/{len(pdf_paths)}: {pdf_path.name}")

        output_path = summarizer.generate_summary(pdf_path)

        progress_callback(f"✓ {pdf_path.name} complete")

    return "All summaries generated!"
```

### 2. Timeline Visualization

```python
import matplotlib.pyplot as plt
from datetime import datetime

def visualize_timeline(course_folder):
    """Show reading timeline for a course"""
    summaries = list(course_folder.rglob("*_summary.md"))

    dates = []
    titles = []

    for summary_path in summaries:
        # Parse frontmatter to get date and title
        content = summary_path.read_text(encoding='utf-8')
        # ... parsing logic ...
        dates.append(generated_date)
        titles.append(title)

    # Create timeline plot
    plt.figure(figsize=(12, 6))
    plt.plot(dates, range(len(dates)), 'o-')
    plt.yticks(range(len(dates)), titles)
    plt.xlabel("Date")
    plt.title(f"Reading Timeline: {course_folder.name}")
    plt.show()
```

### 3. Concept Graph

```python
import networkx as nx
import matplotlib.pyplot as plt

def build_concept_graph(course_folder):
    """Visualize connections between readings"""
    G = nx.Graph()

    summaries = list(course_folder.rglob("*_summary.md"))

    for summary_path in summaries:
        # Parse summary to extract:
        # - Reading title (node)
        # - Referenced previous readings (edges)
        # - Key concepts (node attributes)
        pass

    # Draw graph
    nx.draw(G, with_labels=True, node_color='lightblue')
    plt.show()
```

### 4. Export Options

```python
def export_to_notion(summary_path):
    """Export summary to Notion"""
    import notion_client

    notion = notion_client.Client(auth=notion_api_key)

    # Parse summary markdown
    # Create Notion page with structured blocks
    pass

def export_to_anki(summary_path):
    """Generate Anki flashcards from summary"""
    import genanki

    # Extract key terms from Section II
    # Create Anki deck with term/definition cards
    pass
```

## State Management

### Option 1: File System (Simple)
- Continue using markdown files
- GUI reads from file system
- No additional database needed

### Option 2: SQLite (Advanced)
- Store metadata in database
- Faster searches
- Keep markdown files as source of truth

```python
import sqlite3

def build_reading_database(global_master_path):
    """Build searchable database from summaries"""
    conn = sqlite3.connect('readings.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY,
            title TEXT,
            author TEXT,
            course TEXT,
            week TEXT,
            thesis TEXT,
            summary_path TEXT,
            generated_date TEXT
        )
    ''')

    # Parse all summaries and insert
    # ...

    conn.commit()
    conn.close()
```

## Error Handling in GUI

```python
from academic_summarizer.utils.exceptions import (
    PDFExtractionError,
    APIError,
    ValidationError
)

try:
    output_path = summarizer.generate_summary(pdf_path)
except PDFExtractionError as e:
    show_error_dialog(
        "PDF Extraction Failed",
        f"Could not extract text from PDF: {e}\n\n"
        "The PDF may be scanned or password-protected."
    )
except APIError as e:
    show_error_dialog(
        "API Error",
        f"Failed to generate summary: {e}\n\n"
        "Check your API key in settings."
    )
except ValidationError as e:
    show_error_dialog(
        "Invalid Output",
        f"Generated summary is missing sections: {e.missing_sections}\n\n"
        "Try generating again."
    )
```

## Testing GUI

### Unit Tests (Core Logic)
```python
# These tests already exist for core logic
pytest tests/
```

### GUI Tests (PyQt)
```python
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt

def test_file_selection(qtbot):
    """Test file selection dialog"""
    window = MainWindow()
    qtbot.addWidget(window)

    # Simulate file selection
    # ...

    assert window.pdf_path is not None
```

### Integration Tests (Web GUI)
```python
from flask import Flask
import pytest

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_summarize_endpoint(client):
    """Test summary generation endpoint"""
    response = client.post('/api/summarize', json={
        'pdf_path': 'test.pdf'
    })

    assert response.status_code == 200
```

## Packaging & Distribution

### PyQt Desktop App

```bash
# Install PyInstaller
pip install pyinstaller

# Create executable
pyinstaller --onefile --windowed gui_main.py
```

### Web App

```bash
# Run locally
flask run

# Deploy to server
gunicorn app:app
```

## Summary Checklist

When migrating to GUI:

- [ ] Choose framework (Flask/PyQt/Tkinter)
- [ ] Import core modules (no modifications needed)
- [ ] Implement file selection dialog
- [ ] Add progress feedback (threading or callbacks)
- [ ] Create settings panel for API key
- [ ] Build master file viewer
- [ ] Add historical context preview
- [ ] Handle errors with user-friendly messages
- [ ] Test with real PDFs
- [ ] Package for distribution

## Additional Resources

- PyQt6 Documentation: https://doc.qt.io/qtforpython-6/
- Flask Documentation: https://flask.palletsprojects.com/
- React Documentation: https://react.dev/

For system architecture details, see [ARCHITECTURE.md](ARCHITECTURE.md).
