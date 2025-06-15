import json
import os
import time
from datetime import datetime
from pathlib import Path

# Create the tool_logs directory if it doesn't exist
TOOL_LOGS_DIR = Path(__file__).parent / "tool_logs"
TOOL_LOGS_DIR.mkdir(exist_ok=True)

def log_tool_performance(tool_name, tool_input, tool_output, execution_time, success):
    """
    Log tool performance metrics to a JSON file
    
    Args:
        tool_name (str): Name of the tool
        tool_input (any): Input provided to the tool
        tool_output (any): Output returned by the tool
        execution_time (float): Time taken to execute the tool in seconds
        success (bool): Whether the tool execution was successful
    """
    # Create a log entry
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": tool_name,
        "input": str(tool_input),
        "output_length": len(str(tool_output)) if tool_output else 0,
        "success": success,
        "latency": round(execution_time, 3)
    }
    
    # Generate filename based on date
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = TOOL_LOGS_DIR / f"tool_performance_{date_str}.json"
    
    # Append to existing logs or create new file
    try:
        if log_file.exists():
            with open(log_file, "r+") as f:
                try:
                    logs = json.load(f)
                    logs.append(log_entry)
                    f.seek(0)
                    json.dump(logs, f, indent=2)
                except json.JSONDecodeError:
                    # File exists but is empty or invalid JSON
                    f.seek(0)
                    json.dump([log_entry], f, indent=2)
        else:
            with open(log_file, "w") as f:
                json.dump([log_entry], f, indent=2)
    except Exception as e:
        print(f"Error logging tool performance: {str(e)}")

def get_tool_performance_stats(days=7):
    """
    Get performance statistics for tools over the specified number of days
    
    Args:
        days (int): Number of days to analyze
        
    Returns:
        dict: Tool performance statistics
    """
    stats = {}
    
    # Get list of log files to analyze
    log_files = list(TOOL_LOGS_DIR.glob("tool_performance_*.json"))
    log_files.sort(reverse=True)  # Most recent first
    log_files = log_files[:days]  # Limit to specified number of days
    
    for log_file in log_files:
        try:
            if log_file.exists():
                with open(log_file, "r") as f:
                    logs = json.load(f)
                    for log in logs:
                        tool_name = log["tool"]
                        if tool_name not in stats:
                            stats[tool_name] = {
                                "calls": 0,
                                "success_count": 0,
                                "failure_count": 0,
                                "total_latency": 0,
                                "avg_latency": 0
                            }
                        
                        stats[tool_name]["calls"] += 1
                        if log["success"]:
                            stats[tool_name]["success_count"] += 1
                        else:
                            stats[tool_name]["failure_count"] += 1
                        stats[tool_name]["total_latency"] += log["latency"]
                        stats[tool_name]["avg_latency"] = stats[tool_name]["total_latency"] / stats[tool_name]["calls"]
        except Exception as e:
            print(f"Error reading tool performance log {log_file}: {str(e)}")
    
    return stats 