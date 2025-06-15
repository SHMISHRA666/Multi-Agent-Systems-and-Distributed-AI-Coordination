import asyncio
import json
import os
import random
import time
import unittest
import pytest
import re
from datetime import datetime
from pathlib import Path
from typing import List

# Add project root to Python path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.agent_loop2 import AgentLoop
from mcp_servers.multiMCP import MultiMCP
import yaml

# Configuration constants
MIN_SLEEP = 1   # Minimum sleep time between runs (seconds)
MAX_SLEEP = 3   # Maximum sleep time between runs (seconds)
DEBUG_MODE = os.environ.get('DEBUG_MODE', '0') == '1'  # Debug mode flag

def generate_document_queries() -> List[str]:
    """Generate queries based on document content in the documents folder"""
    queries = []
    docs_dir = Path("mcp_servers/documents")
    
    # Process text files
    for file_path in docs_dir.glob("*.txt"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
                # Extract sentences and create queries
                sentences = re.split(r'[.!?]', content)
                sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
                
                # Sample some sentences to create queries
                for sentence in random.sample(sentences, min(5, len(sentences))):
                    keywords = re.findall(r'\b[A-Za-z]{4,}\b', sentence)
                    if len(keywords) >= 3:
                        sampled_keywords = random.sample(keywords, min(3, len(keywords)))
                        query = f"Tell me about {' '.join(sampled_keywords)} from {file_path.stem}"
                        queries.append(query)
                
                # Add specific queries for this file
                queries.append(f"Summarize the content of {file_path.stem}")
                queries.append(f"What are the key points in {file_path.stem}?")
        except Exception as e:
            if DEBUG_MODE:
                print(f"Error processing {file_path}: {str(e)}")
    
    # Process markdown files
    for file_path in docs_dir.glob("*.md"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
                # Extract headings and create queries
                headings = re.findall(r'#+\s+(.*)', content)
                for heading in headings:
                    queries.append(f"What does {file_path.stem} say about {heading}?")
                
                # Extract entities and create queries
                entities = re.findall(r'\*\*(.*?)\*\*|`(.*?)`|\[(.*?)\]', content)
                flat_entities = [item for sublist in entities for item in sublist if item]
                for entity in flat_entities[:5]:  # Limit to 5 entities per file
                    queries.append(f"Tell me about {entity} mentioned in {file_path.stem}")
                
                # Add specific queries for this file
                queries.append(f"Summarize the {file_path.stem} document")
                queries.append(f"What are the main topics covered in {file_path.stem}?")
        except Exception as e:
            if DEBUG_MODE:
                print(f"Error processing {file_path}: {str(e)}")
    
    # Add queries for PDF files
    for file_path in docs_dir.glob("*.pdf"):
        queries.append(f"Extract and summarize the content from {file_path.name}")
        queries.append(f"What information can you find in {file_path.name}?")
        queries.append(f"What are the key points in the {file_path.stem} document?")
    
    # Add queries for DOCX files
    for file_path in docs_dir.glob("*.docx"):
        queries.append(f"Extract and summarize the content from {file_path.name}")
        queries.append(f"What information can you find in {file_path.name}?")
    
    return queries

def generate_math_queries() -> List[str]:
    """Generate math queries that work with the available math tools"""
    queries = []
    
    # Basic arithmetic queries
    for _ in range(10):
        a = random.randint(1, 100)
        b = random.randint(1, 100)
        operations = [
            f"What is {a} + {b}?",
            f"Calculate {a} - {b}",
            f"Multiply {a} and {b}",
            f"Divide {a} by {b} and give the result"
        ]
        queries.append(random.choice(operations))
    
    # Advanced math queries
    advanced_queries = [
        "What is the factorial of 7?",
        "Calculate the cube root of 27",
        "What is 2 raised to the power of 10?",
        "Calculate the sine of 45 degrees",
        "What is the cosine of 60 degrees?",
        "Calculate the tangent of 30 degrees",
        "What is the remainder when 17 is divided by 5?",
        "Generate the first 10 Fibonacci numbers",
        "Convert the strings 'hello' and 'world' to their ASCII values and sum them",
        "Calculate the exponential sum of the list [1, 2, 3, 4, 5]"
    ]
    queries.extend(advanced_queries)
    
    return queries

def generate_web_search_queries() -> List[str]:
    """Generate web search queries"""
    queries = [
        "What is the latest news about artificial intelligence?",
        "Tell me about the current stock market trends",
        "What are the recent developments in renewable energy?",
        "Who won the most recent Nobel Prize in Physics?",
        "What are the top movies released this year?",
        "Tell me about recent advancements in quantum computing",
        "What is the current weather in New York?",
        "What are the latest smartphone models?",
        "Tell me about the most recent space exploration missions",
        "What are the trending technologies in 2023?",
        "Who is the current CEO of Microsoft?",
        "What are the latest developments in electric vehicles?",
        "Tell me about recent breakthroughs in medical research",
        "What are the top universities in the world?",
        "Tell me about the latest advancements in robotics"
    ]
    return queries

def generate_general_queries() -> List[str]:
    """Generate general queries that test various agent capabilities"""
    queries = [
        "Write a short poem about technology",
        "Tell me a joke about programming",
        "What's your favorite color and why?",
        "If you could travel anywhere, where would you go?",
        "What's the meaning of life?",
        "Tell me about yourself",
        "What can you do?",
        "How do I make a good pasta sauce?",
        "What are the best practices for learning a new language?",
        "How can I improve my productivity?",
        "What are some good exercises for staying fit?",
        "Tell me about the history of the internet",
        "What books would you recommend for someone interested in science?",
        "How does blockchain technology work?",
        "What are some tips for better sleep?",
        "How can I reduce my carbon footprint?",
        "What are the benefits of meditation?",
        "How do I start investing in stocks?",
        "What are some healthy breakfast ideas?",
        "How can I improve my public speaking skills?"
    ]
    return queries

# Generate all queries
def generate_all_queries() -> List[str]:
    """Generate all queries for testing"""
    all_queries = []
    all_queries.extend(generate_document_queries())
    all_queries.extend(generate_math_queries())
    all_queries.extend(generate_web_search_queries())
    all_queries.extend(generate_general_queries())
    
    # Ensure we have at least 100 queries
    if len(all_queries) < 100:
        # Add more general queries if needed
        additional_needed = 100 - len(all_queries)
        for i in range(additional_needed):
            all_queries.append(f"General test query #{i+1}")
    
    # Shuffle the queries
    random.shuffle(all_queries)
    
    print(f"Generated {len(all_queries)} queries for testing")
    return all_queries

# Get the number of test runs from environment or use the number of queries
TEST_QUERIES = generate_all_queries()
MAX_RUNS = int(os.environ.get('MAX_TEST_RUNS', len(TEST_QUERIES)))

def log_result(result, log_dir="tests/simulation_logs"):
    """
    Log the result of an agent run to a JSON file.
    
    Args:
        result: The agent session result
        log_dir: Directory to store logs
    """
    # Create log directory if it doesn't exist
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Create a timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{result.session_id}.json"
    filepath = Path(log_dir) / filename
    
    # Count completed steps across all plan versions
    completed_steps = 0
    for plan_version in result.plan_versions:
        for step in plan_version["steps"]:
            if step.status == "completed":
                completed_steps += 1
    
    # Extract the latest plan details
    latest_plan = None
    plan_steps = []
    plan_id = None
    
    if result.plan_versions:
        latest_plan = result.plan_versions[-1]
        
        # Try to get plan_id - handle different data structures
        if isinstance(latest_plan, dict):
            plan_id = latest_plan.get("plan_id", f"plan-{len(result.plan_versions)}")
            steps = latest_plan.get("steps", [])
        else:
            # If it's not a dict, try to access attributes
            plan_id = getattr(latest_plan, "plan_id", f"plan-{len(result.plan_versions)}")
            steps = getattr(latest_plan, "steps", [])
        
        # Process steps
        for step in steps:
            # Handle both dictionary and object formats
            if isinstance(step, dict):
                step_data = {
                    "description": step.get("description", "No description"),
                    "status": step.get("status", "unknown"),
                    "tool_name": step.get("tool_name", None),
                    "tool_input": step.get("tool_input", None),
                    "tool_output": step.get("tool_output", None)
                }
            else:
                step_data = {
                    "description": getattr(step, "description", "No description"),
                    "status": getattr(step, "status", "unknown"),
                    "tool_name": getattr(step, "tool_name", None) if hasattr(step, "tool_name") else None,
                    "tool_input": getattr(step, "tool_input", None) if hasattr(step, "tool_input") else None,
                    "tool_output": getattr(step, "tool_output", None) if hasattr(step, "tool_output") else None
                }
            plan_steps.append(step_data)
    
    # Extract relevant data from the result
    log_data = {
        "session_id": result.session_id,
        "original_query": result.original_query,
        "timestamp": datetime.now().isoformat(),
        "plan_versions": len(result.plan_versions),
        "steps_executed": completed_steps,
        "solution_summary": result.state.get("solution_summary", ""),
        "original_goal_achieved": result.state.get("original_goal_achieved", False),
        "confidence": result.state.get("confidence", 0),
        "latest_plan": {
            "plan_id": plan_id,
            "steps": plan_steps
        }
    }
    
    # Save to file
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2)
    
    print(f"✅ Log saved to: {filepath}")
    return filepath

class TestSimulator:
    def setup_class(self):
        """Setup for the entire test class"""
        # Create log directory
        log_dir = Path("tests/simulation_logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create summary file
        self.summary_file = log_dir / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.summary_data = {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "runs": []
        }
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Setup for each test method"""
        # Ensure summary_data is initialized
        if not hasattr(self, 'summary_data'):
            self.setup_class()
        yield
        
    @pytest.mark.asyncio
    async def test_stress_simulator(self):
        """Run the stress test simulation with multiple agent runs"""
        # Make sure summary_data is initialized
        if not hasattr(self, 'summary_data'):
            self.setup_class()
            
        # Load MCP server configuration
        with open("config/mcp_server_config.yaml", "r") as f:
            profile = yaml.safe_load(f)
            mcp_servers_list = profile.get("mcp_servers", [])
            configs = list(mcp_servers_list)

        # Initialize MCP
        multi_mcp = MultiMCP(server_configs=configs)
        await multi_mcp.initialize()
        
        # Create agent loop
        loop = AgentLoop(
            perception_prompt_path="prompts/perception_prompt.txt",
            decision_prompt_path="prompts/decision_prompt.txt",
            multi_mcp=multi_mcp,
            strategy="exploratory"
        )
        
        # Determine how many queries to run
        num_runs = min(MAX_RUNS, len(TEST_QUERIES))
        print(f"\n===== Starting Stress Test Simulation with {num_runs} unique queries =====\n")
        
        for i in range(num_runs):
            # Get the query for this run
            query = TEST_QUERIES[i]
            print(f"\n----- Run {i+1}/{num_runs} -----")
            print(f"Query: {query}")
            
            try:
                # Run the agent
                start_time = time.time()
                result = await loop.run(query)
                end_time = time.time()
                execution_time = end_time - start_time
                
                # Log the result
                log_path = log_result(result)
                
                # Update summary
                run_data = {
                    "run_id": i+1,
                    "query": query,
                    "session_id": result.session_id,
                    "success": True,
                    "execution_time": execution_time,
                    "log_file": str(log_path)
                }
                self.summary_data["runs"].append(run_data)
                self.summary_data["successful_runs"] += 1
                
                print(f"✅ Run {i+1} completed in {execution_time:.2f} seconds")
                
                # Print more details in debug mode
                if DEBUG_MODE:
                    print(f"  Session ID: {result.session_id}")
                    print(f"  Plan versions: {len(result.plan_versions)}")
                    print(f"  Solution: {result.state.get('solution_summary', '')[:100]}...")
                
            except Exception as e:
                # Log the failure
                print(f"❌ Run {i+1} failed: {str(e)}")
                
                if DEBUG_MODE:
                    import traceback
                    traceback.print_exc()
                
                # Update summary
                run_data = {
                    "run_id": i+1,
                    "query": query,
                    "success": False,
                    "error": str(e)
                }
                self.summary_data["runs"].append(run_data)
                self.summary_data["failed_runs"] += 1
            
            # Update total runs
            self.summary_data["total_runs"] += 1
            
            # Save summary after each run
            self.summary_data["end_time"] = datetime.now().isoformat()
            with open(self.summary_file, "w", encoding="utf-8") as f:
                json.dump(self.summary_data, f, indent=2)
            
            # Sleep between runs to avoid rate limits
            if i < num_runs - 1:  # Don't sleep after the last run
                sleep_time = random.uniform(MIN_SLEEP, MAX_SLEEP)
                print(f"Sleeping for {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
        
        # Final summary
        print("\n===== Stress Test Simulation Complete =====")
        print(f"Total runs: {self.summary_data['total_runs']}")
        print(f"Successful runs: {self.summary_data['successful_runs']}")
        print(f"Failed runs: {self.summary_data['failed_runs']}")
        print(f"Success rate: {(self.summary_data['successful_runs'] / self.summary_data['total_runs']) * 100:.2f}%")
        print(f"Summary saved to: {self.summary_file}")
        
        # Assert that we completed all runs
        assert self.summary_data["total_runs"] == num_runs, f"Expected {num_runs} runs, got {self.summary_data['total_runs']}"

if __name__ == "__main__":
    # Run the test directly
    pytest.main(["-v", "-s", __file__]) 