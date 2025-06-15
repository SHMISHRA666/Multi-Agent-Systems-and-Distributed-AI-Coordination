import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory.tool_logger import get_tool_performance_stats

class ToolPerformanceAnalyzer:
    """
    Analyzes and visualizes tool performance data from logs
    """
    def __init__(self, days=7):
        """
        Initialize the analyzer with data from the specified number of days
        
        Args:
            days (int): Number of days of data to analyze
        """
        self.days = days
        self.stats = get_tool_performance_stats(days=days)
        
    def print_summary(self):
        """Print a summary of tool performance statistics"""
        if not self.stats:
            print("No tool performance data available")
            return
            
        print(f"\n{'=' * 60}")
        print(f"TOOL PERFORMANCE SUMMARY (Last {self.days} days)")
        print(f"{'=' * 60}")
        print(f"{'Tool Name':<25} {'Calls':<8} {'Success Rate':<15} {'Avg Latency':<15}")
        print(f"{'-' * 60}")
        
        for tool_name, tool_stats in sorted(self.stats.items(), 
                                           key=lambda x: x[1]['calls'], 
                                           reverse=True):
            calls = tool_stats['calls']
            success_rate = tool_stats['success_count'] / calls if calls > 0 else 0
            success_rate_str = f"{success_rate*100:.1f}%"
            avg_latency = tool_stats['avg_latency']
            
            print(f"{tool_name:<25} {calls:<8} {success_rate_str:<15} {avg_latency:.3f}s")
            
    def plot_success_rates(self, output_file=None):
        """
        Plot tool success rates
        
        Args:
            output_file (str, optional): Path to save the plot. If None, display the plot.
        """
        if not self.stats:
            print("No tool performance data available")
            return
            
        tools = []
        success_rates = []
        
        for tool_name, tool_stats in sorted(self.stats.items(), 
                                           key=lambda x: x[1]['success_count'] / x[1]['calls'] if x[1]['calls'] > 0 else 0, 
                                           reverse=True):
            if tool_stats['calls'] > 0:
                tools.append(tool_name)
                success_rates.append(tool_stats['success_count'] / tool_stats['calls'])
                
        if not tools:
            print("No tools with calls found")
            return
                
        plt.figure(figsize=(10, 6))
        plt.bar(tools, success_rates)
        plt.xlabel('Tool')
        plt.ylabel('Success Rate')
        plt.title(f'Tool Success Rates (Last {self.days} days)')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        if output_file:
            plt.savefig(output_file)
        else:
            plt.show()
            
    def plot_latency(self, output_file=None):
        """
        Plot tool latency
        
        Args:
            output_file (str, optional): Path to save the plot. If None, display the plot.
        """
        if not self.stats:
            print("No tool performance data available")
            return
            
        tools = []
        latencies = []
        
        for tool_name, tool_stats in sorted(self.stats.items(), 
                                           key=lambda x: x[1]['avg_latency'], 
                                           reverse=False):
            if tool_stats['calls'] > 0:
                tools.append(tool_name)
                latencies.append(tool_stats['avg_latency'])
                
        if not tools:
            print("No tools with calls found")
            return
                
        plt.figure(figsize=(10, 6))
        plt.bar(tools, latencies)
        plt.xlabel('Tool')
        plt.ylabel('Average Latency (seconds)')
        plt.title(f'Tool Average Latency (Last {self.days} days)')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        if output_file:
            plt.savefig(output_file)
        else:
            plt.show()
            
def main():
    """Main function to run the analyzer"""
    analyzer = ToolPerformanceAnalyzer(days=7)
    analyzer.print_summary()
    
    # Check if matplotlib is available
    try:
        import matplotlib
        # Create reports directory if it doesn't exist
        reports_dir = Path(__file__).parent / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        # Generate and save plots
        date_str = datetime.now().strftime("%Y-%m-%d")
        analyzer.plot_success_rates(output_file=reports_dir / f"tool_success_rates_{date_str}.png")
        analyzer.plot_latency(output_file=reports_dir / f"tool_latency_{date_str}.png")
        print(f"\nReports saved to {reports_dir}")
    except ImportError:
        print("\nMatplotlib not available. Skipping visualization.")
        
if __name__ == "__main__":
    main() 