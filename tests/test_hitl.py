import unittest
import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Ensure imports are relative to project root
from action.executor import run_user_code
from mcp_servers.multiMCP import MultiMCP

class MockTool:
    def __init__(self, name, should_fail=False):
        self.name = name
        self.should_fail = should_fail

    def run(self, *args):
        if self.should_fail:
            raise Exception("Simulated tool failure")
        return f"Success from {self.name} with args {args}"

@pytest.mark.asyncio
class TestHITL:
    async def asyncSetUp(self):
        # Create a mock MultiMCP instance
        self.multi_mcp = MagicMock(spec=MultiMCP)
        
        # Create mock tools
        self.working_tool = MockTool("working_tool")
        self.failing_tool = MockTool("failing_tool", should_fail=True)
        
        # Setup mock get_all_tools
        self.multi_mcp.get_all_tools.return_value = [self.working_tool, self.failing_tool]
        
        # Setup mock function_wrapper with proper behavior
        def mock_function_wrapper(tool_name, *args):
            if tool_name == "failing_tool":
                raise Exception("Simulated tool failure")
            return f"Success from {tool_name} with args {args}"
            
        self.multi_mcp.function_wrapper = MagicMock(side_effect=mock_function_wrapper)

        # Create log directory
        log_dir = Path("memory/tool_failures")
        log_dir.mkdir(parents=True, exist_ok=True)

    @pytest.fixture(autouse=True)
    async def setup_and_teardown(self):
        await self.asyncSetUp()
        yield
        # Cleanup if needed
        pass

    async def test_log_directory_exists(self):
        """Test that the tool failure log directory is created"""
        log_dir = Path("memory/tool_failures")
        assert log_dir.exists(), "Tool failures log directory should be created"

    async def test_successful_tool_execution(self):
        """Test that working tools execute normally"""
        code = """
result = working_tool("test_input")
"""
        result = await run_user_code(code, self.multi_mcp)
        print(f"Successful tool execution result: {result}")  # Debug output
        
        assert result["status"] == "success", f"Expected success but got {result}"
        assert "Success from working_tool" in str(result["result"])

    @patch('builtins.input', return_value="Human provided answer")
    async def test_tool_failure_with_hitl(self, mock_input):
        """Test that failing tools trigger HITL and log properly"""
        code = """
result = failing_tool("test_input")
"""
        result = await run_user_code(code, self.multi_mcp)
        print(f"HITL result: {result}")  # Debug output
        
        # Check HITL response
        assert result["status"] == "success_with_human_intervention", f"Expected success_with_human_intervention but got {result}"
        assert result["result"] == "Human provided answer"
        
        # Verify metadata
        assert "metadata" in result
        metadata = result["metadata"]
        assert metadata["source"] == "human"
        assert metadata["original_tool"] == "failing_tool"
        
        # Check logs
        log_dir = Path("memory/tool_failures")
        log_files = list(log_dir.glob("*.jsonl"))
        assert len(log_files) > 0, "Should create log file"
        
        # Verify log content
        with open(log_files[0]) as f:
            log_entry = json.loads(f.readline())
            assert log_entry["tool_name"] == "failing_tool"
            assert log_entry["human_response"]["result"] == "Human provided answer"

    @patch('builtins.input', side_effect=["First response", "Second response"])
    async def test_multiple_tool_failures(self, mock_input):
        """Test handling of multiple tool failures"""
        code = """
result1 = failing_tool("first_test")
result2 = failing_tool("second_test")
result = {
    "status": "success",
    "result": [result1["result"], result2["result"]]
}
"""
        result = await run_user_code(code, self.multi_mcp)
        print(f"Multiple failures result: {result}")  # Debug output
        
        assert result["status"] == "success", f"Expected success but got {result}"
        assert "First response" in str(result["result"])
        assert "Second response" in str(result["result"])

def run_tests():
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestHITL)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)

if __name__ == "__main__":
    # Run tests using asyncio
    asyncio.run(run_tests()) 