import streamlit as st
import anthropic
from datetime import datetime
import sqlite3
import json
from pathlib import Path
import PyPDF2
import io
import docx2txt
import bcrypt
import uuid
from contextlib import contextmanager
from typing import Dict, List, Tuple

# Page configuration
st.set_page_config(
    page_title="Job Buddy",
    page_icon="💼",
    layout="wide"
)

# Database handling
@contextmanager
def get_connection():
    conn = sqlite3.connect('job_buddy.db', check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_connection() as conn:
        c = conn.cursor()
        # Users table
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (id TEXT PRIMARY KEY,
                      username TEXT UNIQUE,
                      password_hash TEXT,
                      created_at TIMESTAMP)''')
        
        # Resumes table with user association
        c.execute('''CREATE TABLE IF NOT EXISTS resumes
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id TEXT,
                      name TEXT,
                      content TEXT,
                      file_type TEXT,
                      created_at TIMESTAMP,
                      FOREIGN KEY(user_id) REFERENCES users(id))''')
        
        # Analysis history with user association
        c.execute('''CREATE TABLE IF NOT EXISTS analysis_history
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id TEXT,
                      job_post TEXT,
                      analysis TEXT,
                      created_at TIMESTAMP,
                      FOREIGN KEY(user_id) REFERENCES users(id))''')
        
        c.execute('CREATE INDEX IF NOT EXISTS idx_resumes_user_id ON resumes(user_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_analysis_user_id ON analysis_history(user_id)')
        conn.commit()

# Initialize database
init_db()

# User Authentication
def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def verify_password(password: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def create_user(username: str, password: str) -> str:
    user_id = str(uuid.uuid4())
    password_hash = hash_password(password)
    
    with get_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('''INSERT INTO users (id, username, password_hash, created_at)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)''',
                     (user_id, username, password_hash))
            conn.commit()
            return user_id
        except sqlite3.IntegrityError:
            return None

def authenticate_user(username: str, password: str) -> str:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id, password_hash FROM users WHERE username = ?', (username,))
        result = c.fetchone()
        if result and verify_password(password, result[1]):
            return result[0]
    return None

# File processing functions
def extract_text_from_pdf(pdf_file) -> str:
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        return " ".join(page.extract_text() for page in pdf_reader.pages)
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return None

def extract_text_from_docx(docx_file) -> str:
    try:
        return docx2txt.process(docx_file)
    except Exception as e:
        st.error(f"Error reading DOCX: {str(e)}")
        return None

# Resume operations
def save_resume(user_id: str, name: str, content: str, file_type: str):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO resumes 
                     (user_id, name, content, file_type, created_at)
                     VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)''',
                 (user_id, name, content, file_type))
        conn.commit()

def get_user_resumes(user_id: str) -> List[Tuple[str, str, str]]:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''SELECT name, content, file_type 
                    FROM resumes 
                    WHERE user_id = ?
                    ORDER BY created_at DESC''', (user_id,))
        return c.fetchall()

def delete_resume(user_id: str, name: str):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM resumes WHERE user_id = ? AND name = ?', 
                 (user_id, name))
        conn.commit()

# Analysis operations
def save_analysis(user_id: str, job_post: str, analysis: str):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO analysis_history 
                     (user_id, job_post, analysis, created_at)
                     VALUES (?, ?, ?, CURRENT_TIMESTAMP)''',
                 (user_id, job_post, analysis))
        conn.commit()

def get_user_analysis_history(user_id: str) -> List[Tuple[str, str, datetime]]:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''SELECT job_post, analysis, created_at 
                    FROM analysis_history 
                    WHERE user_id = ?
                    ORDER BY created_at DESC''', (user_id,))
        return c.fetchall()

# Authentication check
def check_authentication():
    if 'user_id' not in st.session_state:
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.title("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            col3, col4 = st.columns(2)
            with col3:
                if st.button("Login", type="primary"):
                    user_id = authenticate_user(username, password)
                    if user_id:
                        st.session_state.user_id = user_id
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
            
            with col4:
                if st.button("Register"):
                    if username and password:
                        user_id = create_user(username, password)
                        if user_id:
                            st.session_state.user_id = user_id
                            st.success("Registration successful!")
                            st.rerun()
                        else:
                            st.error("Username already exists")
                    else:
                        st.error("Please provide username and password")
        
        with col2:
            st.title("Welcome to Job Buddy")
            st.markdown("""
                #### Your AI-Powered Job Application Assistant
                
                Transform your job search with intelligent application analysis:
                
                🎯 **Smart Job Fit Analysis**  
                ✨ **Custom Resume Tailoring**  
                💡 **Strategic Insights**  
                📝 **Application Assistance**  
                
                Start your smarter job search today!
            """)
        return False
    return True

# Main app
def main():
    if not check_authentication():
        return
        
    st.title("Job Buddy")
    
    # Sidebar for resume management
    with st.sidebar:
        st.header("My Resumes")
        uploaded_file = st.file_uploader("Upload Resume", type=['pdf', 'txt', 'docx'])
        
        if uploaded_file:
            file_name = uploaded_file.name.rsplit('.', 1)[0]
            
            if uploaded_file.type == "application/pdf":
                resume_content = extract_text_from_pdf(uploaded_file)
            elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                resume_content = extract_text_from_docx(uploaded_file)
            else:
                resume_content = uploaded_file.getvalue().decode()
                
            if resume_content:
                st.success("✅ File uploaded successfully")
                if st.button("💾 Save Resume", type="primary"):
                    save_resume(st.session_state.user_id, file_name, 
                              resume_content, uploaded_file.type)
                    st.success(f"✅ Saved: {file_name}")
                    st.rerun()
        
        # Display user's resumes
        st.divider()
        st.subheader("Saved Resumes")
        for name, content, file_type in get_user_resumes(st.session_state.user_id):
            with st.expander(f"📄 {name}"):
                st.text_area("Content", content, height=200)
                if st.button(f"Delete {name}"):
                    delete_resume(st.session_state.user_id, name)
                    st.rerun()
        
        if st.button("🚪 Logout"):
            del st.session_state.user_id
            st.rerun()

    # Main content area
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("🎯 Job Posting Analysis")
        job_post = st.text_area("Paste the job posting here", height=200)
        custom_questions = st.text_area("Custom application questions (Optional)", 
                                      height=100)

        if st.button("🎯 Analyze Job Fit", type="primary"):
            if job_post:
                with st.spinner("Analyzing your fit..."):
                    # Get all user's resumes
                    user_resumes = get_user_resumes(st.session_state.user_id)
                    if not user_resumes:
                        st.error("Please upload at least one resume first")
                        return
                        
                    combined_resume_context = "\n---\n".join(
                        content for _, content, _ in user_resumes
                    )
                    
                    try:
                        client = anthropic.Client(
                            api_key=st.secrets["ANTHROPIC_API_KEY"]
                        )
                        
                        prompt = f"""Job Post: {job_post}
                        Resume Context: {combined_resume_context}
                        Custom Questions: {custom_questions if custom_questions else 'None'}
                        
                        Please analyze this application following the format:
                        
                        ## Initial Assessment
                        ## Match Analysis
                        ## Resume Strategy
                        ## Tailored Resume
                        ## Custom Responses
                        ## Follow-up Actions"""

                        message = client.messages.create(
                            model="claude-3-sonnet-20240229",
                            max_tokens=4096,
                            messages=[{"role": "user", "content": prompt}]
                        )
                        
                        analysis = message.content[0].text
                        save_analysis(st.session_state.user_id, job_post, analysis)
                        
                        # Display analysis
                        st.markdown(analysis)
                        
                    except Exception as e:
                        st.error(f"Analysis error: {str(e)}")
            else:
                st.error("Please provide a job posting")

    with col2:
        st.header("📚 Analysis History")
        history = get_user_analysis_history(st.session_state.user_id)
        
        if history:
            for job_post, analysis, timestamp in history:
                with st.expander(f"Analysis: {timestamp}"):
                    st.markdown(analysis)
        else:
            st.info("Your analysis history will appear here")

if __name__ == "__main__":
    main()
