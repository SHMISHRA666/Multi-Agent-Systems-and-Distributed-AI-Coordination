"""
Tests for the MAX_STEPS and MAX_RETRIES implementation
"""
import pytest
import asyncio
from config.agent_constants import MAX_STEPS, MAX_RETRIES
from action.executor import try_tool_n_times
import os
import sys
import json
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from action.executor import make_tool_proxy
from memory.tool_logger import log_tool_performance, get_tool_performance_stats

# Mock tool function that fails a specified number of times before succeeding
async def mock_failing_tool(fail_count, *args):
    # Static counter to track calls
    if not hasattr(mock_failing_tool, "calls"):
        mock_failing_tool.calls = 0
    
    mock_failing_tool.calls += 1
    
    if mock_failing_tool.calls <= fail_count:
        raise Exception(f"Mock failure {mock_failing_tool.calls}/{fail_count}")
    
    return f"Success after {fail_count} failures"

@pytest.fixture
def reset_mock_tool():
    # Reset the call counter before each test
    if hasattr(mock_failing_tool, "calls"):
        mock_failing_tool.calls = 0
    yield

@pytest.mark.asyncio
async def test_try_tool_success_first_try(reset_mock_tool):
    """Test that try_tool_n_times succeeds when the tool works on first try"""
    result = await try_tool_n_times(lambda *args: asyncio.sleep(0.1, result="Success"), "arg1")
    assert result == "Success"

@pytest.mark.asyncio
async def test_try_tool_success_after_retries(monkeypatch, reset_mock_tool):
    """Test that try_tool_n_times retries and succeeds within MAX_RETRIES"""
    # Mock the tool to succeed on the 2nd try (1 failure)
    result = await try_tool_n_times(lambda *args: mock_failing_tool(1, *args), "arg1")
    assert result == "Success after 1 failures"
    assert mock_failing_tool.calls == 2  # 1 failure + 1 success

@pytest.mark.asyncio
async def test_try_tool_max_retries_exceeded(monkeypatch, reset_mock_tool):
    """Test that try_tool_n_times falls back to HITL after MAX_RETRIES failures"""
    # Mock get_human_input to return a test response
    from unittest.mock import AsyncMock, MagicMock
    
    human_response = {
        "result": "Human intervention result",
        "metadata": {"source": "human", "timestamp": "2023-01-01T00:00:00"}
    }
    
    # Mock both human input and logging functions
    monkeypatch.setattr("action.executor.get_human_input", lambda *args: human_response)
    monkeypatch.setattr("action.executor.log_tool_failure", lambda *args: None)
    
    # Tool that always fails
    result = await try_tool_n_times(lambda *args: mock_failing_tool(MAX_RETRIES + 1, *args), "arg1")
    
    # Should have attempted exactly MAX_RETRIES times before falling back to human input
    assert mock_failing_tool.calls == MAX_RETRIES
    assert result == human_response
    assert result["result"] == "Human intervention result"

async def test_tool_logger():
    """Test the tool performance logging functionality"""
    print("Testing tool performance logging...")
    
    # Test direct logging
    log_tool_performance(
        tool_name="test_tool",
        tool_input={"query": "test query"},
        tool_output={"result": "test result"},
        execution_time=0.5,
        success=True
    )
    
    # Check if log file was created
    date_str = time.strftime("%Y-%m-%d")
    log_file = Path(__file__).parent.parent / "memory" / "tool_logs" / f"tool_performance_{date_str}.json"
    
    if log_file.exists():
        print(f"Log file created: {log_file}")
        with open(log_file, "r") as f:
            logs = json.load(f)
            print(f"Log entries: {len(logs)}")
            print(f"Last log entry: {logs[-1]}")
    else:
        print(f"ERROR: Log file not created: {log_file}")
    
    # Test getting stats
    stats = get_tool_performance_stats()
    print(f"Tool performance stats: {stats}")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_tool_logger()) 