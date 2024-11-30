import streamlit as st
import httpx
from pathlib import Path
import json

# Configure page settings
st.set_page_config(
    page_title="Resume Evaluator",
    page_icon="📝",
    layout="wide"
)

# Define API endpoints
API_BASE_URL = "http://localhost:8000"

def display_match_score(score_text):
    # Extract percentage from text
    try:
        percentage = int(''.join(filter(str.isdigit, score_text.split('\n')[0])))
        st.metric("Match Score", f"{percentage}%")
        # Display explanation
        explanation = score_text.split('\n', 1)[1] if '\n' in score_text else ''
        if explanation:
            st.write(explanation)
    except:
        st.write(score_text)

def display_section(title, content, icon=""):
    with st.expander(f"{icon} {title}", expanded=True):
        if isinstance(content, list):
            for item in content:
                st.write(item)
        else:
            st.write(content)

def main():
    st.title("Resume Evaluator 📝")
    
    # Create two columns for the header
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write("""
        Get personalized feedback on your resume for specific job postings!
        
        1. Upload your resume (PDF format)
        2. Provide the job posting URL
        3. Get instant analysis and recommendations
        """)
    
    with col2:
        st.write("""
        ✨ Features:
        - AI-powered resume analysis
        - Job requirement matching
        - Personalized recommendations
        - Recruiter email draft
        """)

    # File upload for resume
    uploaded_file = st.file_uploader("📄 Upload your resume (PDF)", type=["pdf"])
    job_url = st.text_input("🔗 Enter the job posting URL")

    if uploaded_file and job_url:
        if st.button("🚀 Evaluate Resume"):
            with st.spinner("🔄 Analyzing your resume..."):
                try:
                    # Step 1: Parse resume
                    with st.status("📝 Parsing resume...") as status:
                        # Prepare the file for upload
                        files = {
                            "file": (
                                uploaded_file.name,
                                uploaded_file.getbuffer(),
                                "application/pdf"
                            )
                        }
                        
                        # Make the request
                        resume_response = httpx.post(
                            f"{API_BASE_URL}/parse-resume",
                            files=files,
                            timeout=30.0
                        )
                        
                        if resume_response.status_code != 200:
                            error_detail = "Unknown error"
                            try:
                                error_detail = resume_response.json().get('detail', error_detail)
                            except:
                                error_detail = resume_response.text or error_detail
                            st.error(f"Error parsing resume: {error_detail}")
                            return
                        
                        resume_data = resume_response.json()
                        status.update(label="✅ Resume parsed successfully!", state="complete")

                    # Step 2: Analyze job posting
                    with st.status("🔍 Analyzing job posting...") as status:
                        job_response = httpx.post(
                            f"{API_BASE_URL}/analyze-job",
                            json={"job_url": job_url},
                            timeout=30.0
                        )
                        if job_response.status_code != 200:
                            st.error(f"Error analyzing job posting: {job_response.json().get('detail', 'Unknown error')}")
                            return
                        job_data = job_response.json()
                        status.update(label="✅ Job posting analyzed!", state="complete")

                    # Step 3: Get evaluation
                    with st.status("🤖 Evaluating match...") as status:
                        eval_response = httpx.post(
                            f"{API_BASE_URL}/evaluate",
                            json={
                                "resume_text": resume_data["resume_data"]["text"],
                                "job_description": job_data["job_description"]
                            },
                            timeout=30.0
                        )
                        if eval_response.status_code != 200:
                            st.error(f"Error during evaluation: {eval_response.json().get('detail', 'Unknown error')}")
                            return
                        eval_data = eval_response.json()
                        status.update(label="✅ Evaluation complete!", state="complete")

                    # Display results in a clean layout
                    st.success("Analysis completed successfully!")
                    
                    analysis = eval_data["analysis"]
                    
                    # Display match score
                    if analysis["match_score"]:
                        display_match_score(analysis["match_score"])
                    
                    # Create tabs for different sections
                    tab1, tab2, tab3, tab4 = st.tabs([
                        "🎯 Matching Qualifications",
                        "🔍 Gaps & Missing Skills",
                        "💡 Recommendations",
                        "📧 Email Draft"
                    ])
                    
                    with tab1:
                        if analysis["qualifications_match"]:
                            st.write(analysis["qualifications_match"])
                    
                    with tab2:
                        if analysis["gaps"]:
                            st.write(analysis["gaps"])
                    
                    with tab3:
                        if analysis["recommendations"]:
                            st.write(analysis["recommendations"])
                    
                    with tab4:
                        if analysis["email_draft"]:
                            st.text_area(
                                "Copy and customize this email draft:",
                                analysis["email_draft"],
                                height=300
                            )
                            if st.button("📋 Copy to Clipboard"):
                                st.write("Email draft copied to clipboard!")

                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    st.write("Please try again. If the error persists, check if the job posting URL is accessible.")

if __name__ == "__main__":
    main()
