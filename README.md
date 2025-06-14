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

## Architecture

The system is organized into several key components:

- **Agent**: Core agent loop and session management
- **Perception**: Analyzes user queries and execution results
- **Decision**: Creates execution plans and next steps
- **Action**: Executes tools and handles failures
- **Memory**: Stores session logs and tool performance data
- **MCP Servers**: Distributed tool providers (Math, Documents, Web Search)

## Key Features

### Human-in-the-Loop (HITL)

The system includes fallback mechanisms for:
- Tool execution failures
- Plan failures
- Code execution errors

When failures occur, the system prompts for human input and continues execution with the provided guidance.

### Execution Limits

- Maximum steps per agent run
- Maximum retries for tool execution
- Timeout controls for function execution

### Tool Performance Monitoring

- Logs tool execution time and success/failure rates
- Stores performance metrics for future tool selection optimization
- Records human interventions for analysis

### Stress Testing

Includes a simulator for running multiple agent tests with:
- Rate limiting to avoid API bans
- Comprehensive logging of results
- Performance analysis

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
