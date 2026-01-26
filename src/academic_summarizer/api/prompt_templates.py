"""Prompt templates for generating reading summaries with historical context."""

from typing import Dict, List


SYSTEM_PROMPT = """You are an expert academic reading assistant with expertise in:
- Identifying central arguments and theoretical frameworks
- Extracting key concepts and definitions with precision
- Recognizing methodological approaches and their limitations
- Synthesizing across texts and disciplines
- Generating thought-provoking Socratic discussion questions
- Identifying empirical evidence (sample sizes, effect sizes, statistical methods)
- Surfacing dialectical tensions and counter-positions

Your summaries help students prepare for seminar discussions by focusing on critical engagement rather than passive comprehension. You prioritize:
1. First-principles analysis of underlying assumptions
2. Explicit connections between readings across weeks
3. Quantitative evidence where available (stats, n-sizes, methodologies)
4. Steelmanned opposing viewpoints
5. Verbatim quotes that capture theoretical precision

You make explicit connections between readings to build cumulative understanding across the semester."""


def build_summary_prompt(
    pdf_text: str,
    context: Dict,
    previous_summaries: List[Dict] = None,
) -> str:
    """
    Build prompt for generating reading summary with historical context.

    Args:
        pdf_text: Extracted text from PDF
        context: Course context dictionary (course_code, week, etc.)
        previous_summaries: List of previous summary contexts (optional)

    Returns:
        Formatted prompt string
    """
    previous_summaries = previous_summaries or []

    # Build previous weeks section
    previous_context_section = ""
    if previous_summaries:
        previous_context_section = "\n\nPREVIOUS WEEKS' LEARNING:"
        for prev in previous_summaries:
            week = prev.get("week", "?")
            title = prev.get("title", "Unknown")
            author = prev.get("author", "Unknown")
            thesis = prev.get("thesis", "")
            concepts = prev.get("key_concepts", [])

            previous_context_section += f'\n\nWeek {week} - "{title}" by {author}'
            if thesis:
                previous_context_section += f"\n- Core Thesis: {thesis}"
            if concepts:
                concepts_str = ", ".join(concepts[:5])
                previous_context_section += f"\n- Key Concepts: {concepts_str}"

    # Build paired readings section
    paired_readings_section = ""
    other_readings = context.get("other_readings", [])
    if other_readings:
        paired_readings_section = f"\n- Paired Readings this week: {', '.join(other_readings)}"

    # Build full prompt
    prompt = f"""You are an academic reading assistant. Generate a structured summary of the following academic text for a college-level course.

CONTEXT:
- Course: {context.get('course_code', 'Unknown')} - {context.get('course_name', '')}
- Week/Module: Week {context.get('week', '?')}{' - ' + context.get('module', '') if context.get('module') else ''}{paired_readings_section}{previous_context_section}

READING TEXT:
{pdf_text[:30000]}

OUTPUT REQUIREMENTS:
Generate a markdown-formatted summary with EXACTLY these five sections. Follow this structure precisely:

## I. Syllabus Contextualization (1-2 min read)
- **Course**: {context.get('course_code', 'Unknown')}
- **Week/Module**: Week {context.get('week', '?')}{' - ' + context.get('module', '') if context.get('module') else ''}
- **Theme**: [Extract or infer the module theme from the reading]
- **Paired Readings**: [{', '.join(other_readings) if other_readings else 'None detected'}]
- **Course Objective**: [Infer how this reading serves course learning goals]
- **Discussion Questions**: [Extract if provided in reading, otherwise note "Not provided in reading"]

## II. Core Thesis & Architecture (3-4 min read)
- **Central Argument**: [One clear sentence stating the thesis]
- **Key Terms**: [List 5-7 important terms with precise definitions in format "term: definition". Preserve author's exact terminology.]
- **Framework/Method**: [Describe the theoretical framework or research methodology used]
- **Evidence Base**: [Be specific: n=?, methodology type, effect sizes if reported, limitations acknowledged by author. If purely theoretical, describe the logical structure and types of evidence marshaled. If no empirical evidence, state this explicitly.]
- **Critical Quotes**: [Include 3-4 verbatim quotes that capture:
  (a) The core thesis statement
  (b) A key theoretical move or insight
  (c) The most precise definition of a central concept
  (d) Optional: A surprising or counterintuitive claim
  Include page numbers where detectable. Do not paraphrase—use exact wording.]

## III. Critical Tensions (2 min read)
- **Internal Contradictions**: [Identify any contradictions or tensions within the text's argument]
- **Counter-Positions**: [Provide the steelmanned opposing view—what would the strongest, most charitable critic say? Name specific theorists, schools, or traditions if identifiable. Do not strawman.]
- **Assumptions Under Scrutiny**: [What must be true for this argument to hold? What happens if those assumptions fail?]
- **Unresolved Questions**: [What questions does the reading raise but not fully answer?]
- **Most Contested Claim**: [Quote the most debatable assertion verbatim, with page number if detectable]

## IV. Cross-Reading Synthesis (3-4 min read)
{_build_synthesis_instructions(previous_summaries, other_readings)}

## V. Critical Questions (1-2 min read)
[Generate 3-5 Socratic questions that provoke genuine uncertainty and critical engagement. Select from the following types based on what fits THIS specific reading:]

**Question types to consider (use only those that apply):**
- First-principles: What assumption, if false, would collapse this argument?
- Empirical: What evidence would change the conclusion?
- Application: How would this framework behave under different conditions?
- Dialectical: How might a critic or opposing school respond?
- Synthesis: How does this complicate or extend earlier course readings?
- Methodological: What are the limits of this approach?
- Definitional: Is the author's use of [key term] coherent or contested?

**Requirements:**
- Do NOT force question types that don't fit the reading
- Prioritize questions that would generate genuine disagreement in seminar
- At least one question should be unanswerable from the text alone
- If fewer than 3 question types genuinely apply, generate multiple questions of the same type rather than forcing irrelevant categories

CRITICAL REQUIREMENTS:
- Use markdown formatting throughout
- Target total reading time: **10-12 minutes**
- Include page numbers for quotes where detectable in the text
- Be specific and evidence-based—do not fabricate information not in the text
- Maintain academic rigor and precision
- Preserve author's precise terminology—do not paraphrase technical terms
- When statistics are present, report them exactly (do not round or summarize)
- If the reading lacks empirical evidence, note this explicitly
- Quotes must be verbatim, not paraphrased
- Steelman opposing views—do not strawman critics{_build_historical_reminder(previous_summaries)}
"""

    return prompt


def _build_synthesis_instructions(
    previous_summaries: List[Dict], other_readings: List[str]
) -> str:
    """
    Build synthesis section instructions based on available context.

    Args:
        previous_summaries: List of previous summary contexts
        other_readings: List of other readings this week

    Returns:
        Formatted instructions for Section IV
    """
    if not previous_summaries:
        # No history - focus on this week only
        return """- **Connections to Other Readings This Week**: [How does this relate to other readings assigned this week?]
- **Course Theme Development**: [How does this reading introduce or develop key course themes?]
- **Transdisciplinary Bridges**: [Where relevant: Does this reading connect to organizational theory, learning science, philosophy of technology, labor economics, or human-AI collaboration? Note connections only if genuinely present—do not force.]"""

    # With history - emphasize connections to previous weeks
    return """- **Connections to This Week's Readings**: [How does this relate to other readings assigned this week?]
- **Building on Previous Weeks**: [IMPORTANT: Make explicit connections to concepts from previous weeks. Reference specific ideas, terms, or frameworks from earlier readings and explain how this reading builds upon, challenges, or extends them. Use specific week references.]
- **Course Theme Progression**: [How does this advance or challenge themes developed in earlier weeks?]
- **Transdisciplinary Bridges**: [Where relevant: Does this reading connect to organizational theory, learning science, philosophy of technology, labor economics, or human-AI collaboration? Note connections only if genuinely present—do not force.]

*Note: This section should explicitly reference concepts from previous weeks to demonstrate cumulative learning.*"""


def _build_historical_reminder(previous_summaries: List[Dict]) -> str:
    """
    Build reminder about historical context usage.

    Args:
        previous_summaries: List of previous summary contexts

    Returns:
        Reminder text if history is available
    """
    if not previous_summaries:
        return ""

    return f"""

**IMPORTANT**: You have been provided with context from {len(previous_summaries)} previous week(s) of readings. In Section IV (Cross-Reading Synthesis), you MUST make explicit connections to concepts, frameworks, and ideas from those earlier readings. Reference specific weeks and show how this reading relates to the cumulative learning trajectory of the course."""


def get_system_prompt() -> str:
    """Get the system prompt for API calls."""
    return SYSTEM_PROMPT
