import json
import os
import sys
from pathlib import Path
from datetime import datetime
import argparse
import matplotlib.pyplot as plt
import numpy as np

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def find_latest_summary(log_dir="tests/simulation_logs"):
    """Find the latest summary file in the log directory"""
    log_dir = Path(log_dir)
    if not log_dir.exists():
        print(f"Error: Log directory {log_dir} does not exist")
        return None
    
    summary_files = list(log_dir.glob("summary_*.json"))
    if not summary_files:
        print(f"Error: No summary files found in {log_dir}")
        return None
    
    # Sort by modification time (newest first)
    summary_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return summary_files[0]

def analyze_summary(summary_file):
    """Analyze the summary file and print statistics"""
    with open(summary_file, "r") as f:
        summary = json.load(f)
    
    total_runs = summary["total_runs"]
    successful_runs = summary["successful_runs"]
    failed_runs = summary["failed_runs"]
    success_rate = (successful_runs / total_runs) * 100 if total_runs > 0 else 0
    
    start_time = datetime.fromisoformat(summary["start_time"])
    end_time = datetime.fromisoformat(summary["end_time"])
    duration = (end_time - start_time).total_seconds()
    
    print("\n===== Stress Test Summary =====")
    print(f"Total runs: {total_runs}")
    print(f"Successful runs: {successful_runs} ({success_rate:.2f}%)")
    print(f"Failed runs: {failed_runs} ({100-success_rate:.2f}%)")
    print(f"Total duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
    print(f"Average time per run: {duration/total_runs:.2f} seconds")
    
    # Analyze execution times
    execution_times = [run.get("execution_time", 0) for run in summary["runs"] if run.get("success", False)]
    if execution_times:
        print("\n===== Execution Time Statistics =====")
        print(f"Minimum: {min(execution_times):.2f} seconds")
        print(f"Maximum: {max(execution_times):.2f} seconds")
        print(f"Average: {sum(execution_times)/len(execution_times):.2f} seconds")
        print(f"Median: {sorted(execution_times)[len(execution_times)//2]:.2f} seconds")
    
    # Analyze queries
    queries = {}
    for run in summary["runs"]:
        query = run.get("query", "unknown")
        if query not in queries:
            queries[query] = {"count": 0, "success": 0, "failure": 0}
        
        queries[query]["count"] += 1
        if run.get("success", False):
            queries[query]["success"] += 1
        else:
            queries[query]["failure"] += 1
    
    print("\n===== Query Statistics =====")
    for query, stats in queries.items():
        success_rate = (stats["success"] / stats["count"]) * 100 if stats["count"] > 0 else 0
        print(f"Query: {query}")
        print(f"  Count: {stats['count']}")
        print(f"  Success rate: {success_rate:.2f}%")
    
    return summary, execution_times, queries

def generate_charts(summary, execution_times, queries, output_dir="tests/simulation_logs"):
    """Generate charts for the test results"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Execution time histogram
    if execution_times:
        plt.figure(figsize=(10, 6))
        plt.hist(execution_times, bins=20, alpha=0.7, color='blue')
        plt.xlabel('Execution Time (seconds)')
        plt.ylabel('Frequency')
        plt.title('Distribution of Execution Times')
        plt.grid(True, alpha=0.3)
        plt.savefig(output_dir / "execution_time_histogram.png")
        print(f"Saved execution time histogram to {output_dir / 'execution_time_histogram.png'}")
    
    # Success/failure pie chart
    plt.figure(figsize=(8, 8))
    labels = ['Success', 'Failure']
    sizes = [summary["successful_runs"], summary["failed_runs"]]
    colors = ['#4CAF50', '#F44336']
    plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    plt.axis('equal')
    plt.title('Success vs. Failure Rate')
    plt.savefig(output_dir / "success_rate_pie.png")
    print(f"Saved success rate pie chart to {output_dir / 'success_rate_pie.png'}")
    
    # Query success rates
    if queries:
        query_names = list(queries.keys())
        success_rates = [(q["success"] / q["count"]) * 100 if q["count"] > 0 else 0 for q in queries.values()]
        
        plt.figure(figsize=(12, 8))
        y_pos = np.arange(len(query_names))
        plt.barh(y_pos, success_rates, align='center', alpha=0.7, color='green')
        plt.yticks(y_pos, query_names)
        plt.xlabel('Success Rate (%)')
        plt.title('Query Success Rates')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / "query_success_rates.png")
        print(f"Saved query success rates chart to {output_dir / 'query_success_rates.png'}")

def generate_html_report(summary_file, summary, output_dir="tests/simulation_logs"):
    """Generate an HTML report of the test results"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = output_dir / "stress_test_report.html"
    
    total_runs = summary["total_runs"]
    successful_runs = summary["successful_runs"]
    failed_runs = summary["failed_runs"]
    success_rate = (successful_runs / total_runs) * 100 if total_runs > 0 else 0
    
    start_time = datetime.fromisoformat(summary["start_time"])
    end_time = datetime.fromisoformat(summary["end_time"])
    duration = (end_time - start_time).total_seconds()
    
    # Generate run details HTML
    run_details = ""
    detailed_query_table = ""
    
    # Process each run
    for run in summary["runs"]:
        status = "Success" if run.get("success", False) else "Failed"
        status_icon = "✓" if run.get("success", False) else "✗"
        error = f"<br><strong>Error:</strong> {run.get('error', 'N/A')}" if not run.get("success", False) else ""
        execution_time = f"{run.get('execution_time', 0):.2f}" if run.get("execution_time") else "N/A"
        
        run_details += f"""
        <tr>
            <td>{run.get("run_id", "N/A")}</td>
            <td>{run.get("query", "N/A")}</td>
            <td><span class="{'success' if run.get('success', False) else 'failure'}">{status_icon} {status}</span>{error}</td>
            <td>{execution_time}</td>
            <td>{run.get("session_id", "N/A")}</td>
        </tr>
        """
        
        # Add detailed query and plan information
        query = run.get("query", "N/A")
        session_id = run.get("session_id", "N/A")
        
        # Try to load the detailed log file for this run
        plan_details = "Plan details not available"
        if run.get("log_file") and Path(run.get("log_file")).exists():
            try:
                with open(run.get("log_file"), "r", encoding="utf-8") as f:
                    log_data = json.load(f)
                    
                    # Format plan steps
                    if "latest_plan" in log_data and isinstance(log_data["latest_plan"], dict):
                        plan_steps = log_data["latest_plan"].get("steps", [])
                        if plan_steps:
                            plan_steps_html = ""
                            for i, step in enumerate(plan_steps):
                                if not isinstance(step, dict):
                                    continue
                                    
                                step_status = step.get("status", "unknown")
                                step_class = "success" if step_status == "completed" else "failure" if step_status == "failed" else ""
                                
                                plan_steps_html += f"""
                                <div class="plan-step {step_class}">
                                    <strong>Step {i+1}:</strong> {step.get("description", "No description")}
                                    <br><em>Status: {step_status}</em>
                                </div>
                                """
                            
                            # Get plan ID safely
                            plan_id = log_data["latest_plan"].get("plan_id", "Unknown")
                            
                            plan_details = f"""
                            <div class="plan-container">
                                <h4>Plan ID: {plan_id}</h4>
                                {plan_steps_html}
                            </div>
                            """
            except Exception as e:
                plan_details = f"Error loading plan details: {str(e)}"
        
        detailed_query_table += f"""
        <tr>
            <td>{run.get("run_id", "N/A")}</td>
            <td>{query}</td>
            <td>{plan_details}</td>
            <td><span class="{'success' if run.get('success', False) else 'failure'}">{status}</span></td>
        </tr>
        """
    
    # Create HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Stress Test Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2, h3 {{ color: #333; }}
            .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .charts {{ display: flex; flex-wrap: wrap; justify-content: space-around; margin-bottom: 20px; }}
            .chart {{ margin: 10px; text-align: center; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 30px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #4CAF50; color: white; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
            .success {{ color: green; }}
            .failure {{ color: red; }}
            .plan-container {{ background-color: #f9f9f9; padding: 10px; border-radius: 5px; margin: 5px 0; }}
            .plan-step {{ margin: 5px 0; padding: 5px; border-left: 3px solid #ccc; }}
            .plan-step.success {{ border-left-color: green; }}
            .plan-step.failure {{ border-left-color: red; }}
            .tabs {{ display: flex; margin-bottom: 10px; }}
            .tab {{ padding: 10px 15px; cursor: pointer; background-color: #f1f1f1; margin-right: 2px; }}
            .tab.active {{ background-color: #4CAF50; color: white; }}
            .tab-content {{ display: none; }}
            .tab-content.active {{ display: block; }}
        </style>
        <script>
            function openTab(evt, tabName) {{
                var i, tabcontent, tablinks;
                tabcontent = document.getElementsByClassName("tab-content");
                for (i = 0; i < tabcontent.length; i++) {{
                    tabcontent[i].style.display = "none";
                }}
                tablinks = document.getElementsByClassName("tab");
                for (i = 0; i < tablinks.length; i++) {{
                    tablinks[i].className = tablinks[i].className.replace(" active", "");
                }}
                document.getElementById(tabName).style.display = "block";
                evt.currentTarget.className += " active";
            }}
            
            window.onload = function() {{
                document.getElementById("summaryTab").click();
            }};
        </script>
    </head>
    <body>
        <h1>Autonomous Agent Stress Test Report</h1>
        <p>Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        
        <div class="tabs">
            <button class="tab active" id="summaryTab" onclick="openTab(event, 'summary')">Summary</button>
            <button class="tab" onclick="openTab(event, 'runDetails')">Run Details</button>
            <button class="tab" onclick="openTab(event, 'detailedQueryPlans')">Query Plans & Results</button>
        </div>
        
        <div id="summary" class="tab-content active">
            <div class="summary">
                <h2>Summary</h2>
                <p><strong>Total runs:</strong> {total_runs}</p>
                <p><strong>Successful runs:</strong> {successful_runs} ({success_rate:.2f}%)</p>
                <p><strong>Failed runs:</strong> {failed_runs} ({100-success_rate:.2f}%)</p>
                <p><strong>Start time:</strong> {start_time.strftime("%Y-%m-%d %H:%M:%S")}</p>
                <p><strong>End time:</strong> {end_time.strftime("%Y-%m-%d %H:%M:%S")}</p>
                <p><strong>Total duration:</strong> {duration:.2f} seconds ({duration/60:.2f} minutes)</p>
                <p><strong>Average time per run:</strong> {duration/total_runs:.2f} seconds</p>
            </div>
            
            <div class="charts">
                <div class="chart">
                    <h3>Success vs. Failure Rate</h3>
                    <img src="success_rate_pie.png" alt="Success Rate Pie Chart" width="400">
                </div>
                <div class="chart">
                    <h3>Execution Time Distribution</h3>
                    <img src="execution_time_histogram.png" alt="Execution Time Histogram" width="400">
                </div>
                <div class="chart">
                    <h3>Query Success Rates</h3>
                    <img src="query_success_rates.png" alt="Query Success Rates" width="500">
                </div>
            </div>
        </div>
        
        <div id="runDetails" class="tab-content">
            <h2>Run Details</h2>
            <table>
                <tr>
                    <th>Run ID</th>
                    <th>Query</th>
                    <th>Status</th>
                    <th>Execution Time (s)</th>
                    <th>Session ID</th>
                </tr>
                {run_details}
            </table>
        </div>
        
        <div id="detailedQueryPlans" class="tab-content">
            <h2>Query Plans & Results</h2>
            <p>This table shows the detailed query, plan, and result for each test run.</p>
            <table>
                <tr>
                    <th>Run ID</th>
                    <th>Query</th>
                    <th>Plan</th>
                    <th>Result</th>
                </tr>
                {detailed_query_table}
            </table>
        </div>
    </body>
    </html>
    """
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"\nHTML report generated: {report_file}")
    return report_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Analyze stress test results')
    parser.add_argument('--summary', help='Path to summary JSON file (default: latest)')
    parser.add_argument('--output-dir', default='tests/simulation_logs', help='Output directory for reports')
    args = parser.parse_args()
    
    summary_file = args.summary
    if not summary_file:
        summary_file = find_latest_summary(args.output_dir)
        if not summary_file:
            sys.exit(1)
    
    print(f"Analyzing summary file: {summary_file}")
    summary, execution_times, queries = analyze_summary(summary_file)
    
    try:
        import matplotlib
        generate_charts(summary, execution_times, queries, args.output_dir)
        generate_html_report(summary_file, summary, args.output_dir)
    except ImportError:
        print("\nWarning: matplotlib not installed. Charts will not be generated.")
        print("Install matplotlib with: pip install matplotlib")
        print("HTML report will still be generated without charts.")
        generate_html_report(summary_file, summary, args.output_dir) 