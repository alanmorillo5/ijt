import json

SYSTEM_PROMPT = """You are an expert resume writer specializing in tailoring resumes
for college students applying to internships. You modify resume content
to emphasize relevant experience while remaining truthful. You NEVER
fabricate experience. Output must be perfectly valid JSON matching the provided schema.
DO NOT include any markdown formatting like ```json or any conversational text. Return ONLY the raw JSON object."""

def build_user_prompt(resume_json: dict, job_dict: dict, matched_keywords: list[str], relevant_skills: list[str]) -> str:
    resume_str = json.dumps(resume_json, indent=2)
    
    title = job_dict.get("title", "Unknown Title")
    company = job_dict.get("company", "Unknown Company")
    description = job_dict.get("description", "")
    
    return f"""## Job Description
Title: {title}
Company: {company}

{description}

## Key Requirements Extracted
Matched Keywords: {', '.join(matched_keywords)}

## Current Resume (JSON)
{resume_str}

## Instructions
1. Rewrite experience bullets to emphasize skills matching: {', '.join(matched_keywords)}
2. Reorder skills to prioritize: {', '.join(relevant_skills)}
3. Adjust project descriptions to highlight relevant technologies
4. Keep all facts truthful — only rephrase, reorder, and emphasize
5. Return the COMPLETE modified resume as valid JSON matching the input schema exactly
"""
