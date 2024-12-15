import streamlit as st
import anthropic
from datetime import datetime
import sqlite3
import json
from pathlib import Path
import PyPDF2
import io
import docx2txt

# Page configuration
st.set_page_config(
    page_title="Job Buddy",
    page_icon="💼",
    layout="wide"
)

# Function to extract text from PDF
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

# Function to extract text from DOCX
def extract_text_from_docx(docx_file):
    try:
        text = docx2txt.process(docx_file)
        return text
    except Exception as e:
        st.error(f"Error reading DOCX: {str(e)}")
        return None

# Initialize connection to SQLite db
@st.cache_resource
def init_connection():
    # Using st.secrets to get the database URL from Streamlit Cloud
    db_path = st.secrets.get("DATABASE_URL", "sqlite:///job_buddy.db")
    if db_path.startswith("sqlite:///"):
        db_path = db_path[10:]
    return sqlite3.connect(db_path)

conn = init_connection()

# Initialize database tables
def init_db():
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

init_db()

[... previous authentication code remains the same ...]

# Main app
if check_password():
    [... previous header code remains the same ...]
    
    # Sidebar for resume management
    with st.sidebar:
        st.header("My Resumes")
        
        # Add new resume
        with st.expander("➕ Add New Resume"):
            resume_name = st.text_input("Resume Name")
            upload_type = st.radio("Upload Type", ["File Upload", "Paste Text"])
            
            if upload_type == "File Upload":
                uploaded_file = st.file_uploader("Choose your resume file", type=['pdf', 'txt', 'docx'])
                if uploaded_file is not None and resume_name:
                    file_type = uploaded_file.type
                    if file_type == "application/pdf":
                        resume_content = extract_text_from_pdf(uploaded_file)
                    elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                        resume_content = extract_text_from_docx(uploaded_file)
                    else:  # txt files
                        resume_content = uploaded_file.getvalue().decode()
                    
                    if resume_content:
                        if st.button("Save Resume"):
                            c = conn.cursor()
                            c.execute('INSERT OR REPLACE INTO resumes VALUES (?, ?, ?, CURRENT_TIMESTAMP)',
                                    (resume_name, resume_content, file_type))
                            conn.commit()
                            st.success(f"Saved resume: {resume_name}")
                            st.rerun()
            else:
                resume_content = st.text_area("Paste your resume here")
                if st.button("Save Resume") and resume_name and resume_content:
                    c = conn.cursor()
                    c.execute('INSERT OR REPLACE INTO resumes VALUES (?, ?, ?, CURRENT_TIMESTAMP)',
                            (resume_name, resume_content, 'text/plain'))
                    conn.commit()
                    st.success(f"Saved resume: {resume_name}")
                    st.rerun()

[... rest of the application code remains the same ...]
