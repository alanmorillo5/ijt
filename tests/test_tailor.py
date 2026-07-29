import pytest
import json
from ijt.tailor.extractor import extract_keywords
from ijt.tailor.prompt import build_user_prompt
from ijt.tailor.validator import validate_resume_json, ValidationError
from ijt.tailor.client import tailor_for_job

def test_extract_keywords():
    job_description = "Looking for someone with C++ and React experience. Not a fan of Java or Python though."
    resume_skills = {
        "languages": ["C++", "Java", "Python", "JavaScript", "C"],
        "frameworks": ["React"]
    }
    
    result = extract_keywords(job_description, resume_skills)
    
    matched = result["matched"]
    assert "C++" in matched
    assert "React" in matched
    assert "Java" in matched
    assert "Python" in matched
    
    assert "C" not in matched  # Ensure 'C' is not falsely matched inside C++
    assert "JavaScript" not in matched

def test_build_user_prompt():
    resume_json = {"personal": {"name": "Test"}}
    job_dict = {"title": "SWE", "company": "Tech", "description": "Desc"}
    matched_keywords = ["Python"]
    relevant_skills = ["Python", "Java"]
    
    prompt = build_user_prompt(resume_json, job_dict, matched_keywords, relevant_skills)
    
    assert "SWE" in prompt
    assert "Tech" in prompt
    assert "Python" in prompt
    assert "Java" in prompt
    assert "Desc" in prompt

def test_validate_resume_json_valid():
    valid_json = '''{
        "personal": {},
        "education": [],
        "experience": [],
        "projects": [],
        "skills": {}
    }'''
    data = validate_resume_json(valid_json)
    assert "personal" in data

def test_validate_resume_json_missing_keys():
    missing_keys_json = '''{
        "personal": {},
        "education": []
    }'''
    with pytest.raises(ValidationError):
        validate_resume_json(missing_keys_json)

def test_validate_resume_json_invalid_syntax():
    invalid_json = '''{
        "personal": {name: "unquoted"}
    }'''
    with pytest.raises(ValidationError):
        validate_resume_json(invalid_json)

@pytest.mark.asyncio
async def test_tailor_for_job_success(mocker):
    resume_json = {
        "personal": {}, "education": [], "experience": [], 
        "projects": [], "skills": {"languages": ["Python"]}
    }
    job_dict = {"title": "Test Job", "description": "Python needed."}
    llm_config = {"model": "dummy", "temperature": 0.0}
    
    mock_response = json.dumps(resume_json)
    mocker.patch("ijt.tailor.client.ollama_chat", return_value=mock_response)
    
    result = await tailor_for_job(resume_json, job_dict, llm_config)
    assert result == resume_json
