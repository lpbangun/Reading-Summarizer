"""Setup script for academic summarizer CLI."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="academic-summarizer",
    version="1.0.0",
    description="Generate structured academic reading summaries with cumulative learning",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Academic Summarizer Team",
    python_requires=">=3.9",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "click>=8.1.7",
        "pdfplumber>=0.11.0",
        "pypdf>=4.0.0",
        "openai>=1.12.0",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.6.0",
        "pydantic-settings>=2.0.0",
        "rich>=13.7.0",
        "tenacity>=8.2.3",
        "pyyaml>=6.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-cov>=4.1.0",
            "black>=24.0.0",
            "mypy>=1.8.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "academic-summary=academic_summarizer.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "Topic :: Education",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
