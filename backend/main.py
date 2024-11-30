from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from openai import OpenAI
import json
import requests
from bs4 import BeautifulSoup
from llama_parse import LlamaParse
import tempfile
import shutil
from pathlib import Path
import nest_asyncio

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

load_dotenv()

app = FastAPI()

# Initialize API clients
llama_parse_api_key = os.getenv("LLAMA_PARSE_API_KEY")
if not llama_parse_api_key:
    raise ValueError("LLAMA_PARSE_API_KEY environment variable is not set")

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# Initialize LlamaParse
llama_parser = LlamaParse(
    api_key=llama_parse_api_key,
    language="en",
    result_type="markdown"
)

openai_client = OpenAI(api_key=openai_api_key)

class JobAnalysisRequest(BaseModel):
    job_url: str

class EvaluationRequest(BaseModel):
    resume_text: str
    job_description: str

@app.post("/parse-resume")
async def parse_resume(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Create a temporary directory to store the file
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file_path = Path(temp_dir) / "resume.pdf"
        
        try:
            # Save the uploaded file to the temporary directory
            with temp_file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Parse the PDF using LlamaParse
            documents = llama_parser.load_data(str(temp_file_path))
            
            if not documents:
                raise HTTPException(status_code=400, detail="Could not extract text from the PDF")
            
            resume_text = documents[0].text
            
            # Extract structured information
            structured_data = {
                "text": resume_text,
                "sections": {}
            }
            
            # Try to identify common resume sections
            sections = resume_text.split('\n\n')
            current_section = "General"
            
            for section in sections:
                section = section.strip()
                if section:
                    lower_section = section.lower()
                    if any(header in lower_section for header in ['experience', 'education', 'skills', 'projects', 'certifications']):
                        current_section = section.split('\n')[0]
                        structured_data["sections"][current_section] = []
                    else:
                        if current_section not in structured_data["sections"]:
                            structured_data["sections"][current_section] = []
                        structured_data["sections"][current_section].append(section)
            
            return {"status": "success", "resume_data": structured_data}
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            # Ensure the file is closed
            file.file.close()

@app.post("/analyze-job")
async def analyze_job(request: JobAnalysisRequest):
    try:
        # Fetch job posting content
        response = requests.get(request.job_url)
        response.raise_for_status()
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract text content (you might want to make this more specific based on the job site structure)
        job_text = soup.get_text()
        
        # Clean up the text (remove extra whitespace, etc.)
        job_text = ' '.join(job_text.split())
        
        return {"job_description": job_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/evaluate")
async def evaluate_resume(request: EvaluationRequest):
    try:
        # Prepare the prompt for GPT
        prompt = f"""
        You are an expert resume reviewer. Analyze the following resume against the job description.
        Provide a match percentage and detailed feedback.
        
        Job Description:
        {request.job_description}
        
        Resume:
        {request.resume_text}
        
        Please provide:
        1. A match percentage (0-100%)
        2. Key strengths that align with the job
        3. Areas for improvement
        4. Specific suggestions to better match the job requirements
        """
        
        # Get response from GPT
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert resume reviewer providing constructive feedback."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        # Extract and return the analysis
        analysis = response.choices[0].message.content
        return {"analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
