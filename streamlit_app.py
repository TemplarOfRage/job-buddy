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

# [Previous authentication code remains the same]

if check_password():
    # [Previous header code remains the same]
    
    # Sidebar for resume and instruction management
    with st.sidebar:
        tab1, tab2 = st.tabs(["📄 Resumes", "📋 Instructions"])
        
        with tab1:
            st.header("My Resumes")
            # [Previous resume management code remains the same]
        
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
For any percentage matches mentioned, explain the reasoning behind the percentage."""
                    
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
                    
                    # Split analysis into sections (assuming markdown headers)
                    sections = analysis.split('#')[1:]  # Skip the first empty split
                    
                    # Display each section in its respective tab
                    for tab, section in zip(tabs, sections):
                        with tab:
                            st.markdown(f"#{section}")
                    
                    # Save to history
                    st.session_state.user_data['history'].append({
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'job_post': job_post,
                        'resume': selected_resume,
                        'analysis': analysis
                    })
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
                    
                    sections = entry['analysis'].split('#')[1:]
                    for tab, section in zip(hist_tabs, sections):
                        with tab:
                            st.markdown(f"#{section}")
