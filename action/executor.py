import ast
import asyncio
import time
import builtins
import textwrap
import re
from datetime import datetime
from .hitl import get_human_input, log_tool_failure
from config.agent_constants import MAX_RETRIES
from memory.tool_logger import log_tool_performance

# ───────────────────────────────────────────────────────────────
# CONFIG
# ───────────────────────────────────────────────────────────────
ALLOWED_MODULES = {
    "math", "cmath", "decimal", "fractions", "random", "statistics", "itertools", "functools", "operator", "string", "re", "datetime", "calendar", "time", "collections", "heapq", "bisect", "types", "copy", "enum", "uuid", "dataclasses", "typing", "pprint", "json", "base64", "hashlib", "hmac", "secrets", "struct", "zlib", "gzip", "bz2", "lzma", "io", "pathlib", "tempfile", "textwrap", "difflib", "unicodedata", "html", "html.parser", "xml", "xml.etree.ElementTree", "csv", "sqlite3", "contextlib", "traceback", "ast", "tokenize", "token", "builtins"
}
MAX_FUNCTIONS = 5
TIMEOUT_PER_FUNCTION = 500  # seconds

class KeywordStripper(ast.NodeTransformer):
    """Rewrite all function calls to remove keyword args and keep only values as positional."""
    def visit_Call(self, node):
        self.generic_visit(node)
        if node.keywords:
            # Convert all keyword arguments into positional args (discard names)
            for kw in node.keywords:
                node.args.append(kw.value)
            node.keywords = []
        return node


# ───────────────────────────────────────────────────────────────
# AST TRANSFORMER: auto-await known async MCP tools
# ───────────────────────────────────────────────────────────────
class AwaitTransformer(ast.NodeTransformer):
    def __init__(self, async_funcs):
        self.async_funcs = async_funcs

    def visit_Call(self, node):
        self.generic_visit(node)
        if isinstance(node.func, ast.Name) and node.func.id in self.async_funcs:
            return ast.Await(value=node)
        return node

# ───────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ───────────────────────────────────────────────────────────────
def count_function_calls(code: str) -> int:
    tree = ast.parse(code)
    return sum(isinstance(node, ast.Call) for node in ast.walk(tree))

# Function to try a tool multiple times before requiring human intervention
async def try_tool_n_times(tool_fn, *args, max_retries=None):
    """
    Attempts to execute a tool function up to max_retries times before requiring human intervention.
    
    Args:
        tool_fn: The tool function to execute
        *args: Arguments to pass to the tool function
        max_retries: Maximum number of retries, defaults to MAX_RETRIES from config
        
    Returns:
        The result of the tool execution or human intervention
    """
    if max_retries is None:
        max_retries = MAX_RETRIES
        
    errors = []
    
    for attempt in range(max_retries):
        try:
            result = await tool_fn(*args)
            return result
        except Exception as e:
            errors.append(str(e))
            print(f"Tool execution failed (attempt {attempt+1}/{max_retries}): {str(e)}")
            
            # If we haven't reached max retries, try again
            if attempt < max_retries - 1:
                print(f"Retrying... ({attempt+1}/{max_retries})")
                await asyncio.sleep(1)  # Small delay before retry
            else:
                # We've reached max retries, get human input
                error_summary = "\n".join(errors)
                human_response = get_human_input(
                    f"Tool failed after {max_retries} attempts. Last error: {errors[-1]}", 
                    tool_fn.__name__ if hasattr(tool_fn, "__name__") else "unknown_tool", 
                    args
                )
                log_tool_failure(
                    tool_fn.__name__ if hasattr(tool_fn, "__name__") else "unknown_tool",
                    Exception(f"Failed after {max_retries} attempts: {error_summary}"),
                    args,
                    human_response
                )
                return human_response

def build_safe_globals(mcp_funcs: dict, multi_mcp=None) -> dict:
    safe_globals = {
        "__builtins__": {
            k: getattr(builtins, k)
            for k in ("range", "len", "int", "float", "str", "list", "dict", "print", "sum", "__import__", "isinstance", "next")
        },
        **mcp_funcs,
    }

    for module in ALLOWED_MODULES:
        safe_globals[module] = __import__(module)

    # Store LLM-style result
    safe_globals["final_answer"] = lambda x: safe_globals.setdefault("result_holder", x)
    
    # Add try_tool_n_times utility
    safe_globals["try_tool_n_times"] = try_tool_n_times

    # Optional: add parallel execution
    if multi_mcp:
        async def parallel(*tool_calls):
            try:
                coros = [
                multi_mcp.function_wrapper(tool_name, *args)
                for tool_name, *args in tool_calls
                ]
                return await asyncio.gather(*coros)
               
                
            except Exception as parallel_exception:
                # Handle exceptions within parallel execution
                # without referencing outer exception variables
                print(f"Error in parallel execution: {str(parallel_exception)}")
                raise parallel_exception  # Re-raise to be caught by the outer try/except

        safe_globals["parallel"] = parallel

    return safe_globals


# ───────────────────────────────────────────────────────────────
# MAIN EXECUTOR
# ───────────────────────────────────────────────────────────────
async def run_user_code(code: str, multi_mcp) -> dict:
    start_time = time.perf_counter()
    start_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        func_count = count_function_calls(code)
        if func_count > MAX_FUNCTIONS:
            return {
                "status": "error",
                "error": f"Too many functions ({func_count} > {MAX_FUNCTIONS})",
                "execution_time": start_timestamp,
                "total_time": str(round(time.perf_counter() - start_time, 3))
            }

        tool_funcs = {
            tool.name: make_tool_proxy(tool.name, multi_mcp)
            for tool in multi_mcp.get_all_tools()
        }

        sandbox = build_safe_globals(tool_funcs, multi_mcp)
        local_vars = {}

        cleaned_code = textwrap.dedent(code.strip())
        tree = ast.parse(cleaned_code)

        has_return = any(isinstance(node, ast.Return) for node in tree.body)
        has_result = any(
            isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "result" for t in node.targets
            )
            for node in tree.body
        )
        if not has_return and has_result:
            tree.body.append(ast.Return(value=ast.Name(id="result", ctx=ast.Load())))

        tree = KeywordStripper().visit(tree)
        tree = AwaitTransformer(set(tool_funcs)).visit(tree)
        ast.fix_missing_locations(tree)

        func_def = ast.AsyncFunctionDef(
            name="__main",
            args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
            body=tree.body,
            decorator_list=[]
        )
        wrapper = ast.Module(body=[func_def], type_ignores=[])
        ast.fix_missing_locations(wrapper)

        compiled = compile(wrapper, filename="<user_code>", mode="exec")
        exec(compiled, sandbox, local_vars)
        # print("till here its done 1")
        try:
            timeout = max(3, func_count * TIMEOUT_PER_FUNCTION)
            returned = await asyncio.wait_for(local_vars["__main"](), timeout=timeout)
            
            result_value = returned if returned is not None else sandbox.get("result_holder", "None")

            # If the result is already properly formatted with status, return it directly
            if isinstance(result_value, dict) and "status" in result_value:
                result_value.update({
                    "execution_time": start_timestamp,
                    "total_time": str(round(time.perf_counter() - start_time, 3))
                })
                return result_value

            # Handle human intervention results
            # print("till here its done 2")
            if isinstance(result_value, dict) and "metadata" in result_value and result_value["metadata"].get("source") == "human":
                # print("till here its done 3")
                return {
                    "status": "success_with_human_intervention",
                    "result": result_value["result"],
                    "metadata": result_value["metadata"],
                    "execution_time": start_timestamp,
                    "total_time": str(round(time.perf_counter() - start_time, 3))
                }

            # If result looks like tool error text, extract
            if hasattr(result_value, "isError") and getattr(result_value, "isError", False):
                error_msg = None
                try:
                    error_msg = result_value.content[0].text.strip()
                except Exception:
                    error_msg = str(result_value)

                return {
                    "status": "error",
                    "error": error_msg,
                    "execution_time": start_timestamp,
                    "total_time": str(round(time.perf_counter() - start_time, 3))
                }

            # Else: normal success
            return {
                "status": "success",
                "result": str(result_value),
                "execution_time": start_timestamp,
                "total_time": str(round(time.perf_counter() - start_time, 3))
            }

        except Exception as execution_error:
            # Get human intervention for any exception
            # print("till here its done 4")
            print(f"Error: {str(execution_error)}")
            human_response = get_human_input(str(execution_error), "code_execution", code)
            log_tool_failure("code_execution", execution_error, code, human_response)
            
            return {
                "status": "success_with_human_intervention",
                "result": human_response["result"],
                "metadata": human_response["metadata"],
                "execution_time": start_timestamp,
                "total_time": str(round(time.perf_counter() - start_time, 3))
            }

    except asyncio.TimeoutError:
        # print("till here its done 7")
        return {
            "status": "error",
            "error": f"Execution timed out after {func_count * TIMEOUT_PER_FUNCTION} seconds",
            "execution_time": start_timestamp,
            "total_time": str(round(time.perf_counter() - start_time, 3))
        }
    except Exception as outer_error:
        # Get human intervention for any exception
        # print("till here its done 5")
        human_response = get_human_input(str(outer_error), "code_execution", code)
        log_tool_failure("code_execution", outer_error, code, human_response)
        
        return {
            "status": "success_with_human_intervention",
            "result": human_response["result"],
            "metadata": human_response["metadata"],
            "execution_time": start_timestamp,
            "total_time": str(round(time.perf_counter() - start_time, 3))
        }

# ───────────────────────────────────────────────────────────────
# TOOL WRAPPER
# ───────────────────────────────────────────────────────────────
def make_tool_proxy(tool_name: str, mcp):
    async def _tool_fn(*args):
        start_time = time.perf_counter()
        success = True
        try:
            # Use try_tool_n_times to handle retries automatically
            result = await try_tool_n_times(
                lambda *a: mcp.function_wrapper(tool_name, *a),
                *args
            )
                
            if asyncio.iscoroutine(result):
                result = await result
                
            # Handle CallToolResult objects
            if hasattr(result, 'content'):
                # Extract the content from CallToolResult
                if isinstance(result.content, list):
                    result = [str(item) for item in result.content]
                else:
                    result = str(result.content)
            elif hasattr(result, 'text'):
                # Handle text-based results
                result = str(result.text)
            elif hasattr(result, 'result'):
                # Handle human intervention results
                if isinstance(result, dict) and result.get("metadata", {}).get("source") == "human":
                    success = False
                    execution_time = time.perf_counter() - start_time
                    log_tool_performance(tool_name, args, result, execution_time, success)
                    return result
            
            # Log successful tool execution
            execution_time = time.perf_counter() - start_time
            log_tool_performance(tool_name, args, result, execution_time, success)
            return result
        except Exception as e:
            # This will only be reached if try_tool_n_times itself fails
            success = False
            execution_time = time.perf_counter() - start_time
            print(f"Error in tool proxy for {tool_name}: {str(e)}")
            human_response = get_human_input(str(e), tool_name, args)
            log_tool_failure(tool_name, e, args, human_response)
            log_tool_performance(tool_name, args, human_response, execution_time, success)
            return human_response
    
    return _tool_fn