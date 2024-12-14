import streamlit as st
import anthropic
import yaml
import streamlit_authenticator as stauth
import json
from datetime import datetime
from pathlib import Path
import pickle
from yaml.loader import SafeLoader

# Page configuration
st.set_page_config(
    page_title="Job Buddy",
    page_icon="💼",
    layout="wide"
)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    
if 'user_data' not in st.session_state:
    st.session_state.user_data = {
        'resumes': {},
        'history': []
    }

# Simple authentication
def check_password():
    if not st.session_state.authenticated:
        st.title("Job Buddy Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            if (username == st.secrets["USERNAME"] and 
                password == st.secrets["PASSWORD"]):
                st.session_state.authenticated = True
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")
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
        st.experimental_rerun()
    
    # Sidebar for resume management
    with st.sidebar:
        st.header("📄 My Resumes")
        
        # Add new resume
        with st.expander("➕ Add New Resume"):
            resume_name = st.text_input("Resume Name")
            resume_content = st.text_area("Paste your resume here")
            if st.button("Save Resume"):
                if resume_name and resume_content:
                    st.session_state.user_data['resumes'][resume_name] = resume_content
                    st.success(f"Saved resume: {resume_name}")
                    st.experimental_rerun()
        
        # Display existing resumes
        if st.session_state.user_data['resumes']:
            st.subheader("Saved Resumes")
            for name, content in st.session_state.user_data['resumes'].items():
                with st.expander(f"📄 {name}"):
                    st.text_area("Resume Content", content, height=200, key=f"resume_{name}")
                    if st.button(f"Delete {name}"):
                        del st.session_state.user_data['resumes'][name]
                        st.experimental_rerun()

    # Main content area
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("🎯 Job Posting Analysis")
        job_post = st.text_area("Paste the job posting here", height=200)
        
        # Resume selection
        if st.session_state.user_data['resumes']:
            selected_resume = st.selectbox(
                "Select a resume to use",
                options=list(st.session_state.user_data['resumes'].keys())
            )
        else:
            st.warning("Please add a resume in the sidebar first")
            selected_resume = None
        
        custom_questions = st.text_area("Any custom application questions? (Optional)", height=100)

        if st.button("Analyze Job Fit"):
            if selected_resume and job_post:
                with st.spinner("Analyzing your fit for this role..."):
                    client = anthropic.Client(api_key=st.secrets["ANTHROPIC_API_KEY"])
                    
                    prompt = f"""Job Post: {job_post}
                    Resume: {st.session_state.user_data['resumes'][selected_resume]}
                    Questions: {custom_questions if custom_questions else 'None'}
                    
                    Please analyze the job posting and resume to provide:
                    1. Overall match assessment (percentage and brief explanation)
                    2. Key strengths aligned with the role (bullet points)
                    3. Potential gaps or areas to address (bullet points)
                    4. Suggested resume modifications
                    5. Draft responses to any custom questions
                    
                    Format the response in clear sections with headers and ensure all sections are clearly separated."""
                    
                    message = client.messages.create(
                        model="claude-3-sonnet-20240229",
                        max_tokens=4096,
                        messages=[{
                            "role": "user",
                            "content": prompt
                        }]
                    )
                    
                    analysis = message.content
                    
                    # Save to history
                    st.session_state.user_data['history'].append({
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'job_post': job_post,
                        'resume': selected_resume,
                        'analysis': analysis
                    })
                    
                    st.markdown(analysis)
            else:
                st.error("Please provide both a job posting and select a resume")

    with col2:
        st.header("📚 Analysis History")
        if st.session_state.user_data['history']:
            for i, entry in enumerate(reversed(st.session_state.user_data['history'])):
                with st.expander(f"Analysis {len(st.session_state.user_data['history'])-i}: {entry['timestamp']}"):
                    st.write(f"Resume used: {entry['resume']}")
                    st.write("Analysis:")
                    st.markdown(entry['analysis'])
        else:
            st.info("Your analysis history will appear here")
