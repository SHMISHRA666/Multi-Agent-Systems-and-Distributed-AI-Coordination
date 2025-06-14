import json
from datetime import datetime
from pathlib import Path

def get_human_input(error_message: str, tool_name: str, original_input: any) -> dict:
    """Get human input when a tool fails and format it with metadata."""
    print(f"\n[ERROR] Tool '{tool_name}' failed with error: {error_message}")
    print(f"Original input: {original_input}")
    result = input("\nTool failed. Please provide manual input: ")
    
    return {
        "result": result,
        "metadata": {
            "source": "human",
            "timestamp": datetime.now().isoformat(),
            "original_tool": tool_name,
            "original_error": str(error_message),
            "original_input": original_input
        }
    }

def log_tool_failure(tool_name: str, error: Exception, input_data: any, human_response: dict) -> None:
    """Log tool failure and human intervention to a dedicated log file."""
    log_dir = Path("memory/tool_failures")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "tool_name": tool_name,
        "error": str(error),
        "input_data": input_data,
        "human_response": human_response
    }
    
    log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}_failures.jsonl"
    
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n") 