import streamlit as st
import anthropic
from datetime import datetime
import sqlite3
import json
from pathlib import Path
import PyPDF2
import io
import docx2txt
from contextlib import contextmanager
from typing import Dict, List, Tuple

# Page configuration
st.set_page_config(
    page_title="Job Buddy",
    page_icon="💼",
    layout="wide"
)

# Constants
ANALYSIS_INSTRUCTIONS = """# Job Application Analysis Process

1. Initial Assessment
   - Role Overview: Company, position, level, key focus areas
   - Requirements Analysis: Must-haves vs. nice-to-haves
   - Company Culture Assessment

2. Match Analysis
   - Strong Matches: Perfect fits from current experience (using only provided metrics)
   - Solid Matches: Good matches needing minor reframing
   - Gap Areas: Missing or weak matches
   - Additional Context Needed: Areas where more information might help

3. Resume Tailoring Strategy
   - Format: Using provided resume template
   - Content Adjustments: Keeping all quantitative metrics honest
   - Highlighting Relevant Experience
   - Gap Mitigation Strategies

4. Custom Questions
   - Personalized Response Strategy
   - Writing Style Matching
   - Professional Yet Authentic Tone
   - Key Talking Points

5. Follow-up Actions
   - Additional Experience to Include
   - Skills to Highlight
   - Areas Needing Clarification"""

RESUME_TEMPLATE = """# [Full Name]
[City, State] | [Phone] | [Email]

## Professional Experience

### [Job Title] | [Company Name] | [Location]
*[Date Range]*

**[Category Header]**
- [Achievement/Responsibility with metrics]
- [Achievement/Responsibility with metrics]

## Technical Skills
- [Skill Category]: [List of skills]

## Education
### [Degree]
[Institution] | [Location] | *[Completion Date]*"""

# Database handling
@contextmanager
def get_connection():
    """Thread-safe database connection context manager"""
    conn = sqlite3.connect('job_buddy.db', check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initialize database tables"""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS resumes
                     (name TEXT PRIMARY KEY, 
                      content TEXT, 
                      file_type TEXT,
                      created_at TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS analysis_history
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      job_post TEXT,
                      resume_name TEXT,
                      analysis TEXT,
                      created_at TIMESTAMP)''')
        conn.commit()

# Initialize database
init_db()

# File processing functions
def extract_text_from_pdf(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return None

def extract_text_from_docx(docx_file):
    try:
        text = docx2txt.process(docx_file)
        return text
    except Exception as e:
        st.error(f"Error reading DOCX: {str(e)}")
        return None

# Database operations
def save_resume(name, content, file_type):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO resumes VALUES (?, ?, ?, CURRENT_TIMESTAMP)',
                 (name, content, file_type))
        conn.commit()

def get_resumes():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT name, content, file_type FROM resumes')
        return dict((name, (content, file_type)) for name, content, file_type in c.fetchall())

def delete_resume(name):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM resumes WHERE name = ?', (name,))
        conn.commit()

def save_analysis(job_post, resume_name, analysis):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO analysis_history 
                     (job_post, resume_name, analysis, created_at)
                     VALUES (?, ?, ?, CURRENT_TIMESTAMP)''',
                 (job_post, resume_name, analysis))
        conn.commit()

def get_analysis_history():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''SELECT job_post, resume_name, analysis, created_at 
                    FROM analysis_history 
                    ORDER BY created_at DESC''')
        return c.fetchall()

# Analysis helper functions
def parse_claude_response(analysis: str) -> Dict[str, str]:
    """
    Parse Claude's response into structured sections
    """
    sections = {
        "Initial Assessment": "",
        "Match Analysis": "",
        "Resume Strategy": "",
        "Tailored Resume": "",
        "Custom Responses": "",
        "Follow-up Actions": ""
    }
    
    current_section = ""
    content_buffer = []
    
    for li
