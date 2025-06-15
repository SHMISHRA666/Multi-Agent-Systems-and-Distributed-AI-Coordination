import uuid
import json
import datetime
from perception.perception import Perception
from decision.decision import Decision
from action.executor import run_user_code
from agent.agentSession import AgentSession, PerceptionSnapshot, Step, ToolCode
from memory.session_log import live_update_session
from memory.memory_search import MemorySearch
from mcp_servers.multiMCP import MultiMCP
from action.hitl import get_human_input
from config.agent_constants import MAX_STEPS, MAX_RETRIES


GLOBAL_PREVIOUS_FAILURE_STEPS = 3

class AgentLoop:
    def __init__(self, perception_prompt_path: str, decision_prompt_path: str, multi_mcp: MultiMCP, strategy: str = "exploratory"):
        self.perception = Perception(perception_prompt_path)
        self.decision = Decision(decision_prompt_path, multi_mcp)
        self.multi_mcp = multi_mcp
        self.strategy = strategy

    async def run(self, query: str):
        session = AgentSession(session_id=str(uuid.uuid4()), original_query=query)
        session_memory= []
        self.log_session_start(session, query)
        
        # Track the most recent query, which could be updated by human input
        current_query = query

        memory_results = self.search_memory(current_query)
        perception_result = self.run_perception(current_query, memory_results, memory_results)
        session.add_perception(PerceptionSnapshot(**perception_result))

        if perception_result.get("original_goal_achieved"):
            self.handle_perception_completion(session, perception_result)
            return session

        decision_output = self.make_initial_decision(current_query, perception_result)
        step = session.add_plan_version(decision_output["plan_text"], [self.create_step(decision_output)])
        live_update_session(session)
        print(f"\n[Decision Plan Text: V{len(session.plan_versions)}]:")
        for line in session.plan_versions[-1]["plan_text"]:
            print(f"  {line}")

        # Initialize step counter to enforce MAX_STEPS limit
        step_counter = 0
        
        while step:
            # Check if we've reached the maximum number of steps
            if step_counter >= MAX_STEPS:
                print(f"\n⚠️ Maximum number of steps ({MAX_STEPS}) reached. Stopping execution.")
                session.state.update({
                    "original_goal_achieved": False,
                    "final_answer": "Maximum number of steps reached. Please refine your query or break it into smaller parts.",
                    "confidence": 0.5,
                    "reasoning_note": f"Execution stopped after {MAX_STEPS} steps due to step limit.",
                    "solution_summary": f"⚠️ Maximum steps ({MAX_STEPS}) reached. The agent could not complete the task within the step limit."
                })
                live_update_session(session)
                break
                
            step_result = await self.execute_step(step, session, session_memory)
            step_counter += 1
            
            if step_result is None:
                break  # 🔐 protect against CONCLUDE/NOP cases
                
            # Update the current query if human input was provided
            if step_result.execution_result and isinstance(step_result.execution_result, dict) and step_result.execution_result.get("status") == "success_with_human_intervention":
                current_query = step_result.execution_result.get("result", current_query)
                
            step = self.evaluate_step(step_result, session, current_query)

        return session

    def log_session_start(self, session, query):
        print("\n=== LIVE AGENT SESSION TRACE ===")
        print(f"Session ID: {session.session_id}")
        print(f"Query: {query}")

    def search_memory(self, query):
        print("Searching Recent Conversation History")
        searcher = MemorySearch()
        results = searcher.search_memory(query)
        if not results:
            print("❌ No matching memory entries found.\n")
        else:
            print("\n🎯 Top Matches:\n")
            for i, res in enumerate(results, 1):
                print(f"[{i}] File: {res['file']}\nQuery: {res['query']}\nResult Requirement: {res['result_requirement']}\nSummary: {res['solution_summary']}\n")
        return results

    def run_perception(self, query, memory_results, session_memory=None, snapshot_type="user_query", current_plan=None):
        combined_memory = (memory_results or []) + (session_memory or [])
        perception_input = self.perception.build_perception_input(
            raw_input=query, 
            memory=combined_memory, 
            current_plan=current_plan, 
            snapshot_type=snapshot_type
        )
        perception_result = self.perception.run(perception_input)
        print("\n[Perception Result]:")
        print(json.dumps(perception_result, indent=2, ensure_ascii=False))
        return perception_result

    def handle_perception_completion(self, session, perception_result):
        print("\n✅ Perception fully answered the query.")
        session.state.update({
            "original_goal_achieved": True,
            "final_answer": perception_result.get("solution_summary", "Answer ready."),
            "confidence": perception_result.get("confidence", 0.95),
            "reasoning_note": perception_result.get("reasoning", "Handled by perception."),
            "solution_summary": perception_result.get("solution_summary", "Answer ready.")
        })
        live_update_session(session)

    def make_initial_decision(self, query, perception_result):
        decision_input = {
            "plan_mode": "initial",
            "planning_strategy": self.strategy,
            "original_query": query,
            "perception": perception_result
        }
        decision_output = self.decision.run(decision_input)
        return decision_output

    def create_step(self, decision_output):
        return Step(
            index=decision_output["step_index"],
            description=decision_output["description"],
            type=decision_output["type"],
            code=ToolCode(tool_name="raw_code_block", tool_arguments={"code": decision_output["code"]}) if decision_output["type"] == "CODE" else None,
            conclusion=decision_output.get("conclusion"),
        )

    async def execute_step(self, step, session, session_memory):
        print(f"\n[Step {step.index}] {step.description}")

        if step.type == "CODE":
            print("-" * 50, "\n[EXECUTING CODE]\n", step.code.tool_arguments["code"])
            executor_response = await run_user_code(step.code.tool_arguments["code"], self.multi_mcp)
            step.execution_result = executor_response
            step.status = "completed"
            
            # Special handler for PDF content summarization
            if isinstance(executor_response, dict) and isinstance(executor_response.get('result'), str) and 'extract_pdf' in step.code.tool_arguments["code"]:
                pdf_content = executor_response.get('result', '')
                if pdf_content and '## Page' in pdf_content:
                    print("\n📄 PDF content detected. Using perception engine to summarize...")
                    # Use perception engine to summarize the PDF content
                    summary_result = self.summarize_pdf_content(pdf_content)
                    executor_response['result'] = summary_result
                    step.execution_result = executor_response
            
            # Handle HITL response
            if executor_response.get("status") == "success_with_human_intervention":
                print("\n🤖 Human intervention detected!")
                print(f"Human response: {executor_response['result']}")

                try:
                    # Continue with the human's response as new input
                    perception_result = self.run_perception(
                        query=executor_response.get('result'),
                        memory_results=session_memory,
                        current_plan=session.plan_versions[-1]["plan_text"],
                        snapshot_type="step_result"
                    )

                    step.perception = PerceptionSnapshot(**perception_result)
                    
                    # Initialize failure_memory
                    failure_memory = {
                        "query": step.description,
                        "result_requirement": "Human intervention",
                        "solution_summary": str(executor_response.get('result', ''))[:300]
                    }
                    session_memory.append(failure_memory)

                    if len(session_memory) > GLOBAL_PREVIOUS_FAILURE_STEPS:
                        session_memory.pop(0)

                    live_update_session(session)
                    return step
                    
                except Exception as e:
                    print(f"\n⚠️ Error in perception after HITL: {str(e)}")
                    return step
            else:
                perception_result = self.run_perception(
                query=executor_response.get('result', 'Tool Failed'),
                memory_results=session_memory,
                current_plan=session.plan_versions[-1]["plan_text"],
                snapshot_type="step_result"
                )
                step.perception = PerceptionSnapshot(**perception_result)

                # Initialize failure_memory
                failure_memory = {
                    "query": step.description,
                    "result_requirement": "Tool execution",
                    "solution_summary": str(step.execution_result)[:300]
                }
                session_memory.append(failure_memory)

                if len(session_memory) > GLOBAL_PREVIOUS_FAILURE_STEPS:
                        session_memory.pop(0)

                live_update_session(session)
                return step

        elif step.type == "CONCLUDE":
            print(f"\n💡 Conclusion: {step.conclusion}")
            step.execution_result = step.conclusion
            step.status = "completed"

            perception_result = self.run_perception(
                query=step.conclusion,
                memory_results=session_memory,
                current_plan=session.plan_versions[-1]["plan_text"],
                snapshot_type="step_result"
            )
            step.perception = PerceptionSnapshot(**perception_result)
            session.mark_complete(step.perception, final_answer=step.conclusion)
            live_update_session(session)
            return None  # Signal completion

        elif step.type == "NOP":
            print(f"\n❓ Clarification needed: {step.description}")
            step.status = "clarification_needed"
            
            # Get human input for any clarification needed
            human_response = get_human_input(
                f"Clarification needed: {step.description}", 
                "clarification_request", 
                step.description
            )
            
            print(f"\n🤖 Human intervention provided: {human_response['result']}")
            
            # Run perception on the human response
            perception_result = self.run_perception(
                query=human_response['result'],
                memory_results=session_memory,
                current_plan=session.plan_versions[-1]["plan_text"] if session.plan_versions else [],
                snapshot_type="user_query"
            )
            
            # Store the perception result in the step
            step.perception = PerceptionSnapshot(**perception_result)
            
            # Update step execution result with human response
            step.execution_result = {
                "status": "success_with_human_intervention",
                "result": human_response['result']
            }
            
            # Store a record of this step for memory
            failure_memory = {
                "query": step.description,
                "result_requirement": "Human intervention",
                "solution_summary": f"Human provided: {human_response['result'][:300]}"
            }
            session_memory.append(failure_memory)
            
            if len(session_memory) > GLOBAL_PREVIOUS_FAILURE_STEPS:
                session_memory.pop(0)
            
            live_update_session(session)
            
            # Return the step to be evaluated by evaluate_step
            return step
            
    def summarize_pdf_content(self, pdf_content):
        """
        Helper function to summarize PDF content using the perception engine.
        This avoids having to use code execution for summarization.
        """
        try:
            # Extract the key points from the PDF content
            lines = pdf_content.split('\n')
            key_points = []
            current_page = ""
            
            for line in lines:
                line = line.strip()
                if not line or line == "---":
                    continue
                    
                if line.startswith("## Page"):
                    current_page = line
                elif line:
                    key_points.append(line)
            
            # Create a summary
            if key_points:
                summary = "Key points from the PDF:\n\n"
                summary += "\n".join(f"- {point}" for point in key_points if point)
                return summary
            else:
                return "The PDF content could not be summarized. No text content was found."
        except Exception as e:
            print(f"Error summarizing PDF content: {e}")
            return pdf_content  # Return original content if summarization fails

    def evaluate_step(self, step, session, query):
        # print("step", step)
        
        # If this step has human intervention, use that as the new query
        if step.execution_result and isinstance(step.execution_result, dict) and step.execution_result.get("status") == "success_with_human_intervention":
            # Update the query with the human input
            query = step.execution_result.get("result", query)
            print(f"\n📝 Using human input as new query: {query[:100]}{'...' if len(query) > 100 else ''}")
            
        if step.perception.original_goal_achieved:
            print("\n✅ Goal achieved.")
            session.mark_complete(step.perception)
            live_update_session(session)
            return None
        elif step.perception.local_goal_achieved:
            return self.get_next_step(session, query, step)
        else:
            print("\n🔁 Step unhelpful. Replanning.")
            decision_output = self.decision.run({
                "plan_mode": "mid_session",
                "planning_strategy": self.strategy,
                "original_query": query,
                "current_plan_version": len(session.plan_versions),
                "current_plan": session.plan_versions[-1]["plan_text"],
                "completed_steps": [s.to_dict() for s in session.plan_versions[-1]["steps"] if s.status == "completed"],
                "current_step": step.to_dict()
            })
            step = session.add_plan_version(decision_output["plan_text"], [self.create_step(decision_output)])

            print(f"\n[Decision Plan Text: V{len(session.plan_versions)}]:")
            for line in session.plan_versions[-1]["plan_text"]:
                print(f"  {line}")

            return step

    def get_next_step(self, session, query, step):
        next_index = step.index + 1
        total_steps = len(session.plan_versions[-1]["plan_text"])
        if next_index < total_steps:
            # If this step has human intervention, use that as the new query
            if step.execution_result and isinstance(step.execution_result, dict) and step.execution_result.get("status") == "success_with_human_intervention":
                # Update the query with the human input
                query = step.execution_result.get("result", query)
                print(f"\n📝 Using human input as new query for next step: {query[:100]}{'...' if len(query) > 100 else ''}")
                
            decision_output = self.decision.run({
                "plan_mode": "mid_session",
                "planning_strategy": self.strategy,
                "original_query": query,
                "current_plan_version": len(session.plan_versions),
                "current_plan": session.plan_versions[-1]["plan_text"],
                "completed_steps": [s.to_dict() for s in session.plan_versions[-1]["steps"] if s.status == "completed"],
                "current_step": step.to_dict()
            })
            step = session.add_plan_version(decision_output["plan_text"], [self.create_step(decision_output)])

            print(f"\n[Decision Plan Text: V{len(session.plan_versions)}]:")
            for line in session.plan_versions[-1]["plan_text"]:
                print(f"  {line}")

            return step

        else:
            print("\n✅ No more steps.")
            return None