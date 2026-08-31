import json

class ValidationError(Exception):
    pass

def validate_resume_json(json_str: str) -> dict:
    """
    Validate LLM output matches JSON schema and structural requirements.
    Strips markdown formatting if present.
    """
    # First remove any complete <think> blocks
    import re
    json_str = re.sub(r'<think>.*?</think>', '', json_str, flags=re.DOTALL)
    
    # Try to find JSON inside markdown blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', json_str, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Fallback to finding the outermost curly braces
        start = json_str.find('{')
        end = json_str.rfind('}')
        if start != -1 and end != -1 and end >= start:
            json_str = json_str[start:end+1]
        else:
            json_str = json_str.strip()
        
    try:
        data = json.loads(json_str.strip())
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON generated: {e}")

    # Validate structural requirements
    required_keys = ["personal", "education", "experience", "projects", "skills"]
    for key in required_keys:
        if key not in data:
            raise ValidationError(f"Missing required key in JSON: {key}")
            
    return data
