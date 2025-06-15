import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    print(f"Python path: {sys.path}")
    
    import pytest
    import argparse
    
    parser = argparse.ArgumentParser(description='Run agent tests')
    parser.add_argument('--test', choices=['hitl', 'simulator', 'all'], default='all',
                        help='Which test to run (hitl, simulator, or all)')
    parser.add_argument('--runs', type=int, default=100,
                        help='Number of runs for the simulator test (default: 100)')
    parser.add_argument('--debug', action='store_true',
                        help='Run in debug mode with more verbose output')
    args = parser.parse_args()
    
    # Set environment variable for number of runs
    if args.runs != 100:
        os.environ['MAX_TEST_RUNS'] = str(args.runs)
    
    # Set debug mode if requested
    if args.debug:
        os.environ['DEBUG_MODE'] = '1'
    
    exit_code = 0
    
    if args.test == 'hitl' or args.test == 'all':
        print("Running HITL Tests...")
        print("=" * 50)
        hitl_result = pytest.main(["-v", "-s", "tests/test_hitl.py"])
        if hitl_result != 0:
            exit_code = hitl_result
    
    if args.test == 'simulator' or args.test == 'all':
        print("\nRunning Stress Test Simulator...")
        print("=" * 50)
        simulator_result = pytest.main(["-v", "-s", "tests/test_simulator.py"])
        if simulator_result != 0:
            exit_code = simulator_result
            
    sys.exit(exit_code) 