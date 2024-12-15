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

CLAUDE_PROMPT = """Please analyze this job application following a structured format:

## Initial Assessment
[Your assessment of the role, company, and requirements]

## Match Analysis
[Detailed analysis of matches and gaps]

## Resume Strategy
[Strategy for resume tailoring]

## Tailored Resume
[Complete tailored resume in markdown format]

## Custom Responses
[Responses to any custom questions]

## Follow-up Actions
[Recommended next steps]"""

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'clear_form' not in st.session_state:
    st.session_state.clear_form = False
if 'show_config' not in st.session_state:
    st.session_state.show_config = False
if 'custom_prompts' not in st.session_state:
    st.session_state.custom_prompts = {
        'analysis_instructions': ANALYSIS_INSTRUCTIONS,
        'resume_template': RESUME_TEMPLATE,
        'claude_prompt': CLAUDE_PROMPT
    }

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
def format_resume_for_export(resume_content: str) -> str:
    """
    Format resume content to be more copy-paste friendly and properly formatted
    """
    # Remove 'markdown' text and backticks if they appear at the start
    resume_content = resume_content.replace('markdown', '', 1).strip()
    resume_content = resume_content.replace('```', '').strip()
    
    # Normalize line endings
    resume_content = resume_content.replace('\r\n', '\n').replace('\r', '\n')
    
    # Add proper spacing around headers and sections
    lines = resume_content.split('\n')
    formatted_lines = []
    
    for i, line in enumerate(lines):
        # Skip empty lines at the start
        if i == 0 and not line.strip():
            continue
            
        # Clean up any remaining backticks in the line
        line = line.replace('```', '').strip()
        
        # Add extra space before headers
        if line.startswith('#'):
            if i > 0 and not lines[i-1].isspace() and not lines[i-1] == '':
                formatted_lines.append('')
            formatted_lines.append(line)
            formatted_lines.append('')  # Add space after header
            
        # Format job entries
        elif line.strip().startswith('###'):
            formatted_lines.append(line)  # Job title
            if i + 1 < len(lines) and not lines[i+1].startswith('*'):
                formatted_lines.append('')  # Add space if date is missing
                
        # Format dates
        elif line.strip().startswith('*') and line.strip().endswith('*'):
            formatted_lines.append(line)
            formatted_lines.append('')  # Add space after date
            
        # Format categories
        elif line.strip().startswith('**'):
            if i > 0 and not lines[i-1] == '':
                formatted_lines.append('')
            formatted_lines.append(line)
            
        # Format bullet points
        elif line.strip().startswith('- '):
            formatted_lines.append(line)
            
        else:
            formatted_lines.append(line)
    
    # Final cleanup of any trailing/leading spaces
    result = '\n'.join(formatted_lines).strip()
    
    # Ensure the result doesn't start with backticks or markdown
    result = result.replace('```markdown', '').replace('```', '').strip()
    
    return result

def parse_claude_response(analysis: str) -> Dict[str, str]:
    """
    Parse Claude's response into structured sections with improved resume handling
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
    started = False
    
    for line in analysis.split('\n'):
        if line.startswith('## '):
            started = True
            # Save previous section content
            if current_section and current_section in sections:
                sections[current_section] = '\n'.join(content_buffer).strip()
            
            # Extract section header
            header = line.lstrip('#').strip()
            
            # Match section header to our expected sections
            if "Resume" in header and "Tailored" in header:
                current_section = "Tailored Resume"
            elif "Initial" in header or "Assessment" in header:
                current_section = "Initial Assessment"
            elif "Match" in header or "Analysis" in header:
                current_section = "Match Analysis"
            elif "Strategy" in header:
                current_section = "Resume Strategy"
            elif "Custom" in header or "Response" in header:
                current_section = "Custom Responses"
            elif "Follow" in header or "Action" in header:
                current_section = "Follow-up Actions"
            
            content_buffer = []
        else:
            if not started and line.strip():
                # Handle content before first section header
                content_buffer.append(line)
            elif current_section:
                content_buffer.append(line)
    
    # Save the final section
    if current_section and current_section in sections:
        sections[current_section] = '\n'.join(content_buffer).strip()
    
    # Clean up the resume section specifically
    if sections["Tailored Resume"]:
        sections["Tailored Resume"] = sections["Tailored Resume"].strip()
        if sections["Tailored Resume"].lower().startswith('markdown'):
            sections["Tailored Resume"] = sections["Tailored Resume"][8:].strip()
    
    return sections

def validate_claude_response(response: str) -> bool:
    """
    Validate that Claude's response contains all required sections
    """
    required_sections = [
        "## Initial Assessment",
        "## Match Analysis",
        "## Resume Strategy",
        "## Tailored Resume",
    ]
    
    return all(section in response for section in required_sections)

def create_pdf_from_markdown(resume_content: str) -> bytes:
    """
    Convert markdown content to PDF using pdfkit and wkhtmltopdf-pack
    """
    import pdfkit
    import markdown2
    from jinja2 import Template
    
    # Convert markdown to HTML
    html_content = markdown2.markdown(resume_content)
    
    # HTML template with styling
    template = Template("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                margin: 1in;
            }
            h1 { font-size: 18px; margin-bottom: 10px; }
            h2 { font-size: 16px; margin-top: 15px; margin-bottom: 10px; }
            h3 { font-size: 14px; margin-top: 12px; margin-bottom: 8px; }
            ul { margin: 5px 0; }
            li { margin: 3px 0; }
        </style>
    </head>
    <body>
        {{ content }}
    </body>
    </html>
    """)
    
    # Render HTML with the template
    html_doc = template.render(content=html_content)
    
    # Configure PDF options
    options = {
        'page-size': 'Letter',
        'margin-top': '0.5in',
        'margin-right': '0.5in',
        'margin-bottom': '0.5in',
        'margin-left': '0.5in',
        'encoding': "UTF-8",
    }
    
    # Generate PDF
    try:
        pdf = pdfkit.from_string(html_doc, False, options=options)
        return pdf
    except Exception as e:
        st.error(f"PDF generation failed: {str(e)}")
        return None

def display_analysis_content(sections: Dict[str, str], unique_id: str = ""):
    """
    Display analysis content with improved resume formatting and PDF export
    """
    tabs = st.tabs([
        "Initial Assessment",
        "Match Analysis",
        "Strategy & Resume",
        "Custom Responses",
        "Follow-up Actions"
    ])
    
    with tabs[0]:
        st.markdown(sections["Initial Assessment"])
    
    with tabs[1]:
        st.markdown(sections["Match Analysis"])
    
    with tabs[2]:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("### Strategy")
            st.markdown(sections["Resume Strategy"])
        with col2:
            st.markdown("### Tailored Resume")
            tailored_resume = sections["Tailored Resume"]
            if tailored_resume:
                # Format the resume content
                formatted_resume = format_resume_for_export(tailored_resume)
                
                st.markdown("### Download Options")
                
                # Generate and offer PDF download
                try:
                    pdf_content = create_pdf_from_markdown(formatted_resume)
                    if pdf_content:
                        st.download_button(
                            "📥 Download as PDF",
                            pdf_content,
                            file_name=f"tailored_resume_{unique_id}.pdf",
                            mime="application/pdf",
                            key=f"download_pdf_{unique_id}"
                        )
                except Exception as e:
                    st.error("PDF generation is currently unavailable. Please use the copy option.")
                
                # Copy to clipboard button
                if st.button("📋 Copy to Clipboard", key=f"copy_{unique_id}"):
                    st.session_state['clipboard'] = formatted_resume
                    st.success("Resume copied to clipboard!")
                
                # Display the formatted resume
                st.markdown("### Preview")
                st.markdown(formatted_resume)
            else:
                st.warning("No tailored resume generated")
    
    with tabs[3]:
        st.markdown(sections["Custom Responses"])
    
    with tabs[4]:
        st.markdown(sections["Follow-up Actions"])
        
def check_password():
    if not st.session_state.authenticated:
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.title("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.button("Login", type="primary"):
                try:
                    if (username == st.secrets["USERNAME"] and 
                            password == st.secrets["PASSWORD"]):
                        st.session_state.authenticated = True
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                except KeyError:
                    st.error("Authentication credentials not properly configured")
        
        with col2:
            st.title("Welcome to Job Buddy")
            st.markdown("""
                #### Your AI-Powered Job Application Assistant
                
                Transform your job search with intelligent application analysis:
                
                🎯 **Smart Job Fit Analysis**  
                Instantly analyze job postings against your resume
                
                ✨ **Custom Resume Tailoring**  
                Get personalized resume optimization suggestions
                
                💡 **Strategic Insights**  
                Receive detailed match analysis and action items
                
                📝 **Application Assistance**  
                Get help with custom application questions
                
                Start your smarter job search today!
            """)
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
    
    # Configuration and Logout buttons in sidebar
    st.sidebar.markdown("---")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("⚙️ Configuration"):
            st.session_state.show_config = not st.session_state.show_config
    with col2:
        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.rerun()
            
    # Configuration panel
    if st.session_state.show_config:
        with st.sidebar.expander("🎯 Analysis Instructions", expanded=True):
            st.session_state.custom_prompts['analysis_instructions'] = st.text_area(
                "Modify Analysis Instructions",
                st.session_state.custom_prompts['analysis_instructions'],
                height=300
            )
        
        with st.sidebar.expander("📄 Resume Template", expanded=True):
            st.session_state.custom_prompts['resume_template'] = st.text_area(
                "Modify Resume Template",
                st.session_state.custom_prompts['resume_template'],
                height=300
            )
        
        with st.sidebar.expander("🤖 Claude Prompt", expanded=True):
            st.session_state.custom_prompts['claude_prompt'] = st.text_area(
                "Modify Claude's Instructions",
                st.session_state.custom_prompts['claude_prompt'],
                height=300
            )
    
    # Sidebar for resume management
    with st.sidebar:
        st.header("My Resumes")
        
        # Add new resume
        with st.expander("➕ Add New Resume"):
            if st.session_state.clear_form:
                st.session_state.clear_form = False
                st.rerun()
            
            resume_name = st.text_input("Resume Name", key="resume_name")
            upload_type = st.radio("Upload Type", ["File Upload", "Paste Text"])
            
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
            
            st.markdown("---")
            st.markdown("#### To save your resume:")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("✍️ Enter a resume name" + (" ✅" if resume_name else ""))
            with col2:
                st.markdown("📄 Add resume content" + (" ✅" if has_content else ""))
            
            save_button = st.button(
                "💾 Save Resume",
                disabled=not (resume_name and has_content),
                help="Both resume name and content are required to save",type="primary"
            )
            
            if save_button:
                if resume_name and has_content:
                    save_resume(resume_name, resume_content, file_type)
                    st.success(f"✅ Successfully saved resume: {resume_name}")
                    st.session_state.clear_form = True
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

        if st.button("🎯 Craft My Application Package", type="primary"):
            if selected_resume and job_post:
                with st.spinner("Analyzing your fit for this role & building your application package..."):
                    try:
                        client = anthropic.Client(api_key=st.secrets["ANTHROPIC_API_KEY"])
                        
                        prompt = f"""Please analyze this job application following a structured format:

## Initial Assessment
[Your assessment of the role, company, and requirements]

## Match Analysis
[Detailed analysis of matches and gaps]

## Resume Strategy
[Strategy for resume tailoring]

## Tailored Resume
[Complete tailored resume in markdown format]

## Custom Responses
[Responses to any custom questions]

## Follow-up Actions
[Recommended next steps]

Job Post: {job_post}
Resume: {resumes[selected_resume][0]}
Custom Questions: {custom_questions if custom_questions else 'None'}

Remember to:
1. Use only quantitative metrics from the original resume
2. Follow the exact resume template format
3. Make the tailored resume immediately usable
4. Keep section headers exactly as shown above"""

                        message = client.messages.create(
                            model="claude-3-sonnet-20240229",
                            max_tokens=4096,
                            messages=[{"role": "user", "content": prompt}]
                        )
                        
                        # Extract the content from the message response
                        analysis = message.content[0].text
                        
                        # Validate the response
                        if validate_claude_response(analysis):
                            # Parse and display the response
                            sections = parse_claude_response(analysis)
                            display_analysis_content(sections, "main")
                            
                            # Save analysis to history
                            save_analysis(job_post, selected_resume, analysis)
                        else:
                            st.error("Failed to generate a complete analysis. Please try again.")
                        
                    except Exception as e:
                        st.error(f"An error occurred during analysis: {str(e)}")
                        st.write("Error details:", e.__class__.__name__)
                        import traceback
                        st.code(traceback.format_exc())
            else:
                st.error("Please provide both a job posting and select a resume")

    with col2:
        st.header("📚 Analysis History")
        history = get_analysis_history()
        
        if history:
            for i, (job_post, resume_name, analysis, timestamp) in enumerate(history):
                with st.expander(f"Analysis {len(history)-i}: {timestamp}"):
                    st.write(f"Resume used: {resume_name}")
                    sections = parse_claude_response(analysis)
                    display_analysis_content(sections, f"history_{i}")
        else:
            st.info("Your analysis history will appear here")
