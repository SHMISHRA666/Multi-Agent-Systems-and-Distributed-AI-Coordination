# Multi-Agent Systems: Distributed AI Coordination

A robust autonomous agent system with human-in-the-loop capabilities, tool monitoring, and stress testing features.

## Overview

This system implements a multi-agent architecture that can:
- Process natural language queries
- Develop execution plans
- Execute tools and code
- Fall back to human intervention when needed
- Monitor and log tool performance
- Enforce execution limits to prevent runaway processes
- Provide memory-based search for past solutions

## Architecture

The system is organized into several key components:

- **Agent**: Core agent loop and session management
- **Perception**: Analyzes user queries and execution results
- **Decision**: Creates execution plans and next steps
- **Action**: Executes tools and handles failures
- **Memory**: Stores session logs and tool performance data
- **MCP Servers**: Distributed tool providers (Math, Documents, Web Search)
- **Heuristics**: Query validation and sanitization

## Key Features

### Human-in-the-Loop (HITL)

The system includes fallback mechanisms for:
- Tool execution failures
- Plan failures
- Code execution errors

When failures occur, the system prompts for human input and continues execution with the provided guidance.

### Execution Limits

- Maximum steps per agent run (configurable via `MAX_STEPS` in `config/agent_constants.py`)
- Maximum retries for tool execution (configurable via `MAX_RETRIES` in `config/agent_constants.py`)
- Timeout controls for function execution

### Tool Retry Mechanism

The system now includes a `try_tool_n_times` utility that:
- Automatically retries failed tool executions up to `MAX_RETRIES` times
- Provides detailed error logging between retry attempts
- Falls back to human intervention if all retries fail
- Can be used in agent code with: `result = await try_tool_n_times(tool_function, *args)`

### Tool Performance Monitoring

- Logs tool execution time and success/failure rates
- Stores performance metrics for future tool selection optimization
- Records human interventions for analysis

The system includes a comprehensive tool performance logging system that:
- Records detailed metrics for each tool execution in JSON format
- Stores logs in `memory/tool_logs/` with daily rotation
- Provides statistics and visualization capabilities
- Automatically adjusts tool priorities based on performance history

To view tool performance statistics and visualizations:
```
python memory/tool_performance_analyzer.py
```

This generates summary reports and visualizations in the `memory/reports/` directory.

#### Tool Logging Details

Logs are stored as JSON files with the naming convention `tool_performance_YYYY-MM-DD.json`. Each file contains an array of log entries for that day.

Example log entry:
```json
{
  "timestamp": "2025-06-15T21:12:23.686760",
  "tool": "test_tool",
  "input": "{'query': 'test query'}",
  "output_length": 25,
  "success": true,
  "latency": 0.5
}
```

#### Key Logging Components

1. **Logging**: `memory/tool_logger.py` provides the `log_tool_performance()` function to log tool metrics.
2. **Statistics**: `get_tool_performance_stats()` function retrieves performance statistics for tools over a specified number of days.
3. **Tool Prioritization**: `agent/model_manager.py` uses the performance statistics to prioritize better-performing tools in the `adjust_tool_priority()` method.
4. **Analysis and Visualization**: `memory/tool_performance_analyzer.py` provides functionality to analyze and visualize tool performance data.

### Memory Search System

The system includes a memory search capability that:
- Stores past queries and their solutions
- Enables semantic search across previous interactions
- Uses fuzzy matching to find relevant past solutions
- Provides context from previous successful interactions

The memory search system is implemented in `memory/memory_search.py` and provides:
- Rapid retrieval of past solutions for similar queries
- Scoring based on query similarity and solution quality
- Automatic extraction of relevant information from session logs

### Query Heuristics

The system includes a robust query validation system in `heuristics/heuristics.py` that:
- Validates URLs in user queries
- Checks file paths for existence and accessibility
- Enforces sentence length limits
- Screens for blacklisted words and content
- Sanitizes potentially problematic inputs
- Provides detailed validation messages

Heuristics can be easily extended by adding new rules to the `QueryHeuristics` class.

### Multiple Agent Strategies

The system supports different agent strategies:
- Exploratory: Focuses on broad exploration of possible solutions
- Focused: Targets specific requirements with precision
- Balanced: Combines exploration with targeted execution

Agent strategies can be configured when initializing the `AgentLoop` class.

### Stress Testing

Includes a simulator for running multiple agent tests with:
- Rate limiting to avoid API bans
- Comprehensive logging of results
- Performance analysis

#### Stress Test Simulator

The stress test simulator (`test_simulator.py`) runs the agent 100+ times with random queries to test its robustness and performance. It includes:

- Random selection from a set of test queries
- Sleep intervals between runs to avoid rate limits
- Logging of results to JSON files
- Summary statistics

#### Running the Tests

To run all tests:

```bash
python tests/run_tests.py
```

To run only the stress test simulator:

```bash
python tests/run_tests.py --test simulator
```

To run only the HITL tests:

```bash
python tests/run_tests.py --test hitl
```

#### Command Line Options

The test runner supports the following command-line options:

- `--test {hitl,simulator,all}`: Which test to run (default: all)
- `--runs N`: Number of runs for the simulator test (default: 100)
- `--debug`: Run in debug mode with more verbose output

Examples:

```bash
# Run 10 simulator tests with debug output
python tests/run_tests.py --test simulator --runs 10 --debug

# Run all tests with 50 simulator runs
python tests/run_tests.py --runs 50
```

#### Using the Batch File

For Windows users, a batch file is provided to simplify running the tests:

```bash
# Run with default settings (10 runs)
run_stress_test.bat

# Run with 20 runs
run_stress_test.bat --runs 20

# Run with debug output
run_stress_test.bat --debug

# Run with 5 runs and debug output
run_stress_test.bat --runs 5 --debug
```

#### Simulator Configuration

You can configure the simulator by modifying the following constants in `test_simulator.py`:

- `MAX_RUNS`: Number of test runs to perform (default: 100)
- `MIN_SLEEP`: Minimum sleep time between runs in seconds (default: 1)
- `MAX_SLEEP`: Maximum sleep time between runs in seconds (default: 3)
- `TEST_QUERIES`: List of test queries to use for the agent

You can also set these values using environment variables:
- `MAX_TEST_RUNS`: Number of test runs
- `DEBUG_MODE`: Set to '1' for debug mode

#### Test Logs and Analysis

The simulator logs results to the `tests/simulation_logs` directory:

- Individual run logs: `<timestamp>_<session_id>.json`
- Summary file: `summary_<timestamp>.json`

To analyze the results of a stress test run:

```bash
python tests/analyze_results.py
```

This will:
1. Find the latest summary file
2. Analyze the results and print statistics
3. Generate charts (requires matplotlib)
4. Create an HTML report

### Multi-MCP Server Architecture

The system uses a distributed MCP (Model-Controller-Provider) server architecture:
- Multiple specialized servers for different capabilities
- Dynamic routing of requests to appropriate servers
- Fault tolerance with server failover
- Configurable server capabilities

MCP servers are defined in `config/mcp_server_config.yaml` and include:
- Document processing capabilities
- Mathematical computation
- Web search functionality
- Code execution

## Getting Started

### Prerequisites

- Python 3.8+
- Required dependencies (install via pip)

### Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -e .
   ```

### Configuration

Configure MCP servers and tool capabilities in:
- `config/mcp_server_config.yaml`
- `config/profiles.yaml`
- `config/models.json`

### Running the Agent

Start the interactive agent:
```
python main.py
```

## Usage

Once running, the agent will prompt for input. Type your query and the agent will:
1. Analyze the query (Perception)
2. Create an execution plan (Decision)
3. Execute the plan step by step (Action)
4. Provide a final answer

Type 'exit' or 'quit' to end the session.

## Development

### Adding New Tools

1. Implement the tool function in an appropriate MCP server
2. Add the tool name to the server's capabilities list in `config/mcp_server_config.yaml`
3. Update any relevant prompts if needed

### Extending the Agent

The modular architecture allows for easy extension:
- Add new perception capabilities in `perception/`
- Create new decision strategies in `decision/`
- Implement additional tool executors in `action/`
