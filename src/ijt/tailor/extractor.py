import re

def extract_keywords(job_description: str, resume_skills: dict) -> dict:
    """
    Extract technical skills, tools, and frameworks from the job description
    and compare against user's resume skills.
    Uses regex for word boundary matching to prevent false positives,
    and processes skills by length descending to prevent substring matches (e.g. 'C' inside 'C++').
    """
    matched_keywords = []
    
    # Flatten resume skills
    all_skills = []
    if isinstance(resume_skills, dict):
        for category, skills in resume_skills.items():
            all_skills.extend(skills)
    elif isinstance(resume_skills, list):
        all_skills = resume_skills
        
    # Remove duplicates but preserve all original skills in output
    unique_skills = list(set(all_skills))
    
    # Sort by length descending
    skills_sorted = sorted(unique_skills, key=len, reverse=True)
    
    desc_copy = job_description
    
    for skill in skills_sorted:
        escaped_skill = re.escape(skill)
        
        pattern = r'(?i)' # Case insensitive flag
        
        # Add word boundary if skill starts with a word character
        if re.match(r'^\w', skill):
            pattern += r'\b'
            
        pattern += escaped_skill
        
        # Add word boundary if skill ends with a word character
        if re.search(r'\w$', skill):
            pattern += r'\b'
            
        if re.search(pattern, desc_copy):
            matched_keywords.append(skill)
            # Replace matched skill with spaces to prevent shorter substring matches (like 'C' after 'C++')
            desc_copy = re.sub(pattern, ' ', desc_copy)
            
    return {
        "matched": matched_keywords,
        "all_skills": all_skills
    }
