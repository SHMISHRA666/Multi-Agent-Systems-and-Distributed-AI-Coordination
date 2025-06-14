from decision.decision import Decision
from mcp_servers.multiMCP import MultiMCP
import json

def test_decision():
    # Example config for MultiMCP, adjust script paths as needed
    server_configs = [
        {"id": "server1", "script": "mcp_servers/mcp_server_1.py"},
        {"id": "server2", "script": "mcp_servers/mcp_server_2.py"},
        {"id": "server3", "script": "mcp_servers/mcp_server_3.py"},
        {"id": "server4", "script": "mcp_servers/mcp_server_4.py"}
    ]
    multi_mcp = MultiMCP(server_configs)
    decision = Decision(
        decision_prompt_path="prompts/decision_prompt.txt",
        multi_mcp=multi_mcp
    )
    result = decision.run(
        decision_input={
            "plan_mode": "initial",
            "planning_strategy": "conservative",
            "original_query": "Find number of BHK variants available in DLF Camelia from local sources.",
            "perception": {
                "entities": ["DLF Camelia", "BHK variants", "local sources"],
                "result_requirement": "Numerical count of distinct BHK configurations...",
                "original_goal_achieved": False,
                "reasoning": "The user wants...",
                "local_goal_achieved": False,
                "local_reasoning": "This is just perception, no data retrieved yet."
            }
        }
    )
    print(json.dumps(result, indent=2))
    print(result)

test_decision()
