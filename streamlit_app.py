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

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    if not st.session_state.authenticated:
        st.title("Job Buddy Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            try:
                if (username == st.secrets["USERNAME"] and 
                        password == st.secrets["PASSWORD"]):
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid username or password")
            except KeyError:
                st.error("Authentication credentials not properly configured")
        return False
    return True

# Main app
if check_password():
    # Header
    st.markdown("""
        <div style='text-align: center; padding: 1rem; background: linear-gradient(90deg, #2563eb, #1d4ed8); color: white; border-radius: 0.5rem; margin-bottom: 2rem;'>
            <h1 style='font-size: 2rem; margin-bottom: 0.5rem;'>Job Buddy</h1>
            <p style='font-size: 1rem; opacity: 0.9;'>Your AI-powered job application assistant</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Logout button in sidebar
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()
    
    # Sidebar for resume management
    with st.sidebar:
        st.header("My Resumes")
        
        # Add new resume
        with st.expander("➕ Add New Resume"):
            resume_name = st.text_input("Resume Name", key="resume_name")
            upload_type = st.radio("Upload Type", ["File Upload", "Paste Text"])
            
            # Track if we have content to save
            has_content = False
            resume_content = None
            file_type = None
            
            if upload_type == "File Upload":
                uploaded_file = st.file_uploader("Choose your resume file", type=['pdf', 'txt', 'docx'])
                if uploaded_file is not None:
                    file_type = uploaded_file.type
                    if file_type == "application/pdf":
                        resume_content = extract_text_from_pdf(uploaded_file)
                    elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                        resume_content = extract_text_from_docx(uploaded_file)
                    else:  # txt files
                        resume_content = uploaded_file.getvalue().decode()
                    
                    if resume_content:
                        has_content = True
                        st.success("✅ File uploaded successfully")
                        st.markdown("### Preview:")
                        st.text_area("Resume Content Preview", resume_content, height=100, disabled=True)
            else:
                resume_content = st.text_area("Paste your resume here", height=200)
                if resume_content:
                    has_content = True
                    file_type = 'text/plain'
            
            # Show requirements and save button
            st.markdown("---")
            st.markdown("#### To save your resume:")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("✍️ Enter a resume name" + (" ✅" if resume_name else ""))
            with col2:
                st.markdown("📄 Add resume content" + (" ✅" if has_content else ""))
            
            # Save button with clear state indication
            save_button = st.button(
                "💾 Save Resume",
                disabled=not (resume_name and has_content),
                help="Both resume name and content are required to save",
                type="primary"
            )
            
            if save_button:
                if resume_name and has_content:
                    save_resume(resume_name, resume_content, file_type)
                    st.success(f"✅ Successfully saved resume: {resume_name}")
                    # Clear the inputs
                    st.session_state.resume_name = ""
                    st.rerun()
                else:
                    if not resume_name:
                        st.error("Please enter a resume name")
                    if not has_content:
                        st.error("Please add resume content")
        
        # Display existing resumes
        resumes = get_resumes()
        
        if resumes:
            st.subheader("Saved Resumes")
            for name, (content, file_type) in resumes.items():
                with st.expander(f"📄 {name}"):
                    st.text_area("Resume Content", content, height=200, key=f"resume_{name}")
                    if st.button(f"Delete {name}"):
                        delete_resume(name)
                        st.rerun()

    # Main content area
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("🎯 Job Posting Analysis")
        job_post = st.text_area("Paste the job posting here", height=200)
        
        # Resume selection
        if resumes:
            selected_resume = st.selectbox(
                "Select a resume to use",
                options=list(resumes.keys())
            )
        else:
            st.warning("Please add a resume in the sidebar first")
            selected_resume = None
        
        custom_questions = st.text_area("Any custom application questions? (Optional)", height=100)

        if st.button("Analyze Job Fit"):
            if selected_resume and job_post:
                with st.spinner("Analyzing your fit for this role..."):
                    try:
                        client = anthropic.Client(api_key=st.secrets["ANTHROPIC_API_KEY"])
                        
                        prompt = f"""Analysis Instructions:
{ANALYSIS_INSTRUCTIONS}

Resume Template to Follow:
{RESUME_TEMPLATE}

Input Data:
Job Post: {job_post}
Resume: {resumes[selected_resume][0]}
Custom Questions: {custom_questions if custom_questions else 'None'}

Please provide a comprehensive analysis following the structure outlined in the instructions above.
Remember:
1. Only use quantitative metrics that are explicitly provided in the resume
2. Identify areas where additional context might be helpful
3. Match writing style to the resume for any custom responses
4. Format the tailored resume exactly according to the template

Format your response with clear markdown headers and ensure each section is thorough and actionable."""
                        
                        message = client.messages.create(
                            model="claude-3-sonnet-20240229",
                            max_tokens=4096,
                            messages=[{
                                "role": "user",
                                "content": prompt
                            }]
                        )
                        
                        analysis = message.content
                        
                        # Save analysis to history
                        save_analysis(job_post, selected_resume, analysis)
                        
                        # Create tabs for organized analysis display
                        tabs = st.tabs([
                            "Initial Assessment",
                            "Match Analysis",
                            "Resume Strategy",
                            "Custom Responses",
                            "Follow-up Actions"
                        ])
                        
                        sections = analysis.split('#')[1:] if '#' in analysis else [analysis]
                        
                        for tab, content in zip(tabs, sections + [''] * (len(tabs) - len(sections))):
                            with tab:
                                if content.strip():
                                    st.markdown(f"#{content}")
                                else:
                                    st.info("No content for this section")
                        
                    except Exception as e:
                        st.error(f"An error occurred during analysis: {str(e)}")
            else:
                st.error("Please provide both a job posting and select a resume")

    with col2:
        st.header("📚 Analysis History")
        history = get_analysis_history()
        
        if history:
            for i, (job_post, resume_name, analysis, timestamp) in enumerate(history):
                with st.expander(f"Analysis {len(history)-i}: {timestamp}"):
                    st.write(f"Resume used: {resume_name}")
                    
                    hist_tabs = st.tabs([
                        "Initial Assessment",
                        "Match Analysis",
                        "Resume Strategy",
                        "Custom Responses",
                        "Follow-up Actions"
                    ])
                    
                    sections = analysis.split('#')[1:] if '#' in analysis else [analysis]
                    
                    for tab, content in zip(hist_tabs, sections + [''] * (len(hist_tabs) - len(sections))):
                        with tab:
                            if content.strip():
                                st.markdown(f"#{content}")
                            else:
                                st.info("No content for this section")
        else:
            st.info("Your analysis history will appear here")
