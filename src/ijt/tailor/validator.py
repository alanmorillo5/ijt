import json

class ValidationError(Exception):
    pass

def validate_resume_json(json_str: str) -> dict:
    """
    Validate LLM output matches JSON schema and structural requirements.
    Strips markdown formatting if present.
    """
    json_str = json_str.strip()
    if json_str.startswith("```json"):
        json_str = json_str[7:]
    elif json_str.startswith("```"):
        json_str = json_str[3:]
    if json_str.endswith("```"):
        json_str = json_str[:-3]
        
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
