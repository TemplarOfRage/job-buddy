import streamlit as st
import anthropic
from datetime import datetime

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
        'history': [],
        'instructions': """# Job Application Analysis Process

1. Initial Assessment
   - Role Overview
   - Company Analysis
   - Key Requirements

2. Match Analysis
   - Strong Matches (Perfect fits from experience)
   - Solid Matches (Good matches needing minor reframing)
   - Gap Areas (Missing or weak matches)

3. Success Probability
   - Overall Match Percentage
   - Key Strengths
   - Challenge Areas
   - Recommended Approach

4. Resume Modification Strategy
   - Priority Changes
   - Additional Optimizations

5. Question Responses
   - Tailored responses to any custom questions
   - Suggested talking points for interviews"""
    }

# Authentication function
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
    
    # Sidebar for resume and instruction management
    with st.sidebar:
        tab1, tab2 = st.tabs(["📄 Resumes", "📋 Instructions"])
        
        with tab1:
            st.header("My Resumes")
            # Add new resume
            with st.expander("➕ Add New Resume"):
                resume_name = st.text_input("Resume Name")
                resume_content = st.text_area("Paste your resume here")
                if st.button("Save Resume"):
                    if resume_name and resume_content:
                        st.session_state.user_data['resumes'][resume_name] = resume_content
                        st.success(f"Saved resume: {resume_name}")
                        st.rerun()
            
            # Display existing resumes
            if st.session_state.user_data['resumes']:
                st.subheader("Saved Resumes")
                for name, content in st.session_state.user_data['resumes'].items():
                    with st.expander(f"📄 {name}"):
                        st.text_area("Resume Content", content, height=200, key=f"resume_{name}")
                        if st.button(f"Delete {name}"):
                            del st.session_state.user_data['resumes'][name]
                            st.rerun()
        
        with tab2:
            st.header("Analysis Instructions")
            instructions = st.text_area(
                "Modify analysis instructions",
                value=st.session_state.user_data['instructions'],
                height=400
            )
            if st.button("Update Instructions"):
                st.session_state.user_data['instructions'] = instructions
                st.success("Instructions updated!")
                st.rerun()

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
                    try:
                        client = anthropic.Client(api_key=st.secrets["ANTHROPIC_API_KEY"])
                        
                        prompt = f"""# Analysis Instructions
{st.session_state.user_data['instructions']}

# Input Data
Job Post: {job_post}
Resume: {st.session_state.user_data['resumes'][selected_resume]}
Custom Questions: {custom_questions if custom_questions else 'None'}

Please provide a comprehensive analysis following the exact structure outlined in the instructions above. 
Format your response with clear markdown headers and ensure each section is thorough and actionable.
Make sure to provide specific examples and evidence from the resume and job posting to support your analysis.
For any percentage matches mentioned, explain the reasoning behind the percentage.

Start each major section with a '#' header for proper formatting."""
                        
                        message = client.messages.create(
                            model="claude-3-sonnet-20240229",
                            max_tokens=4096,
                            messages=[{
                                "role": "user",
                                "content": prompt
                            }]
                        )
                        
                        analysis = message.content
                        
                        # Create tabs for organized analysis display
                        tabs = st.tabs([
                            "Initial Assessment",
                            "Match Analysis",
                            "Success Probability",
                            "Resume Strategy",
                            "Question Responses"
                        ])
                        
                        # More robust handling of the analysis response
                        analysis_text = analysis if isinstance(analysis, str) else str(analysis)
                        sections = analysis_text.split('#') if '#' in analysis_text else [analysis_text]
                        sections = [s for s in sections if s.strip()]  # Remove empty sections
                        
                        # Display in tabs, with fallback handling
                        for tab, content in zip(tabs, sections + [''] * (len(tabs) - len(sections))):
                            with tab:
                                if content.strip():
                                    st.markdown(f"#{content}")
                                else:
                                    st.info("No content for this section")
                        
                        # Save to history
                        st.session_state.user_data['history'].append({
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'job_post': job_post,
                            'resume': selected_resume,
                            'analysis': analysis
                        })
                    except Exception as e:
                        st.error(f"An error occurred during analysis: {str(e)}")
            else:
                st.error("Please provide both a job posting and select a resume")

    with col2:
        st.header("📚 Analysis History")
        if st.session_state.user_data['history']:
            for i, entry in enumerate(reversed(st.session_state.user_data['history'])):
                with st.expander(f"Analysis {len(st.session_state.user_data['history'])-i}: {entry['timestamp']}"):
                    st.write(f"Resume used: {entry['resume']}")
                    
                    # Create tabs for historical analysis
                    hist_tabs = st.tabs([
                        "Initial Assessment",
                        "Match Analysis",
                        "Success Probability",
                        "Resume Strategy",
                        "Question Responses"
                    ])
                    
                    # More robust handling of historical analysis
                    analysis_text = entry['analysis'] if isinstance(entry['analysis'], str) else str(entry['analysis'])
                    sections = analysis_text.split('#') if '#' in analysis_text else [analysis_text]
                    sections = [s for s in sections if s.strip()]
                    
                    for tab, content in zip(hist_tabs, sections + [''] * (len(hist_tabs) - len(sections))):
                        with tab:
                            if content.strip():
                                st.markdown(f"#{content}")
                            else:
                                st.info("No content for this section")
        else:
            st.info("Your analysis history will appear here")
