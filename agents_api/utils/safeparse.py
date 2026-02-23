import re
import json

def safe_parse_json(content):
    # If classifier already returned a dict/list, return it directly
    
    if isinstance(content, (dict, list)):
        return content
    if isinstance(content, str):
        # Extract inner JSON block if model wrapped it in markdown
        cleaned = re.sub(r"```(?:json)?", "", content).strip("` \n")
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {"summary": content, "category": "Other", "exclusion": "none"}
    return {"summary": str(content), "category": "Other", "exclusion": "none"}