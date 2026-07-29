import httpx
import json
from ijt.logging import get_logger
from ijt.tailor.prompt import SYSTEM_PROMPT, build_user_prompt
from ijt.tailor.extractor import extract_keywords
from ijt.tailor.validator import validate_resume_json, ValidationError

logger = get_logger("tailor.client")

async def ollama_chat(messages: list[dict], config: dict) -> str:
    """Ollama API wrapper for stateless chat generation."""
    url = f"{config.get('ollama_host', 'http://localhost:11434')}/api/chat"
    payload = {
        "model": config.get("model", "qwen3.6:27b-q8_0"),
        "messages": messages,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": config.get("temperature", 0.3),
            "num_predict": config.get("max_tokens", 4096),
        }
    }
    
    logger.info(f"Sending request to Ollama: {payload['model']}", extra={"url": url})
    
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]

async def tailor_for_job(resume_json: dict, job_dict: dict, llm_config: dict) -> dict:
    """Tailor resume for a single job. Fresh session per call."""
    
    description = job_dict.get("description", "")
    extracted = extract_keywords(description, resume_json.get("skills", {}))
    matched_keywords = extracted["matched"]
    relevant_skills = extracted["all_skills"]
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(resume_json, job_dict, matched_keywords, relevant_skills)},
    ]
    
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            logger.debug(f"Calling LLM (Attempt {attempt}/{max_retries})")
            response_text = await ollama_chat(messages=messages, config=llm_config)
            
            validated = validate_resume_json(response_text)
            return validated
            
        except ValidationError as e:
            logger.warning(f"Validation failed on attempt {attempt}: {e}")
            if attempt == max_retries:
                raise
            # Append correction message
            messages.append({"role": "assistant", "content": response_text if 'response_text' in locals() else ""})
            messages.append({"role": "user", "content": f"The JSON was invalid: {e}. Please fix it and return ONLY valid JSON."})
            
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            raise
