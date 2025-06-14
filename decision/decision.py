import os
import json
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai.errors import ServerError
import re
from mcp_servers.multiMCP import MultiMCP
import ast

def clean_json_string(json_str: str) -> str:
    """Clean and fix common JSON formatting issues."""
    # Remove any non-JSON content before and after the JSON block
    json_str = re.sub(r'^[^{]*', '', json_str)
    json_str = re.sub(r'[^}]*$', '', json_str)
    
    # Fix common JSON formatting issues
    json_str = re.sub(r',\s*}', '}', json_str)  # Remove trailing commas
    json_str = re.sub(r',\s*]', ']', json_str)  # Remove trailing commas in arrays
    json_str = re.sub(r'}\s*{', '},{', json_str)  # Fix missing commas between objects
    json_str = re.sub(r'\]\s*\[', '],[', json_str)  # Fix missing commas between arrays
    
    # Fix unescaped quotes in strings
    json_str = re.sub(r'(?<!\\)"([^"]*?)(?<!\\)"', r'"\1"', json_str)
    
    return json_str

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

class Decision:
    def __init__(self, decision_prompt_path: str, multi_mcp: MultiMCP, api_key: str | None = None, model: str = "gemini-2.0-flash",  ):
        load_dotenv()
        self.decision_prompt_path = decision_prompt_path
        self.multi_mcp = multi_mcp

        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment or explicitly provided.")
        self.client = genai.Client(api_key=self.api_key)
        

    def run(self, decision_input: dict) -> dict:
        prompt_template = Path(self.decision_prompt_path).read_text(encoding="utf-8")
        function_list_text = self.multi_mcp.tool_description_wrapper()
        tool_descriptions = "\n".join(f"- `{desc.strip()}`" for desc in function_list_text)
        tool_descriptions = "\n\n### The ONLY Available Tools\n\n---\n\n" + tool_descriptions
        full_prompt = f"{prompt_template.strip()}\n{tool_descriptions}\n\n```json\n{json.dumps(decision_input, indent=2)}\n```"

        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=full_prompt
            )
        except ServerError as e:
            print(f"🚫 Decision LLM ServerError: {e}")
            return {
                "step_index": 0,
                "description": "Decision model unavailable: server overload.",
                "type": "NOP",
                "code": "",
                "conclusion": "",
                "plan_text": ["Step 0: Decision model returned a 503. Exiting to avoid loop."],
                "raw_text": str(e)
            }

        raw_text = response.candidates[0].content.parts[0].text.strip()

        try:
            # First try to find JSON block
            match = re.search(r"```json\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
            if not match:
                # If no JSON block found, try to find any JSON-like structure
                match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
                if not match:
                    raise ValueError("No JSON block found")

            json_block = match.group(1)
            cleaned_json = clean_json_string(json_block)
            
            try:
                output = json.loads(cleaned_json)
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON decode failed after cleaning: {e}")
                print("Attempting to extract key fields...")
                
                # Extract key fields using regex
                step_index = re.search(r'"step_index"\s*:\s*(\d+)', cleaned_json)
                description = re.search(r'"description"\s*:\s*"([^"]*)"', cleaned_json)
                type_match = re.search(r'"type"\s*:\s*"([^"]*)"', cleaned_json)
                code_match = re.search(r'"code"\s*:\s*"([^"]*)"', cleaned_json)
                
                output = {
                    "step_index": int(step_index.group(1)) if step_index else 0,
                    "description": description.group(1) if description else "Recovered partial JSON from LLM",
                    "type": type_match.group(1) if type_match else "NOP",
                    "code": code_match.group(1) if code_match else "",
                    "conclusion": "",
                    "plan_text": ["Step 0: Partial plan recovered due to JSON decode error."],
                    "raw_text": raw_text[:1000]
                }

            # Handle flattened or nested format
            if "next_step" in output:
                output.update(output.pop("next_step"))

            defaults = {
                "step_index": 0,
                "description": "Missing from LLM response",
                "type": "NOP",
                "code": "",
                "conclusion": "",
                "plan_text": ["Step 0: No valid plan returned by LLM."]
            }
            for key, default in defaults.items():
                output.setdefault(key, default)

            return output

        except Exception as e:
            print(f"❌ Unrecoverable exception while parsing LLM response: {str(e)}")
            return {
                "step_index": 0,
                "description": f"Exception while parsing LLM output: {str(e)}",
                "type": "NOP",
                "code": "",
                "conclusion": "",
                "plan_text": ["Step 0: Exception occurred while processing LLM response."],
                "raw_text": raw_text[:1000]
            }





