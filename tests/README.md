# Agent Stress Test Simulator

This directory contains tests for the autonomous agent system, including a stress test simulator that runs the agent multiple times to test its robustness and performance.

## Files

- `test_simulator.py`: The main stress test simulator that runs the agent 100+ times with random queries
- `test_hitl.py`: Tests for Human-In-The-Loop functionality
- `run_tests.py`: Script to run all tests
- `analyze_results.py`: Script to analyze test results and generate reports

## Running the Tests

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

### Command Line Options

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

### Using the Batch File

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

## Stress Test Simulator

The stress test simulator (`test_simulator.py`) runs the agent 100+ times with random queries to test its robustness and performance. It includes:

- Random selection from a set of test queries
- Sleep intervals between runs to avoid rate limits
- Logging of results to JSON files
- Summary statistics

### Configuration

You can configure the simulator by modifying the following constants in `test_simulator.py`:

- `MAX_RUNS`: Number of test runs to perform (default: 100)
- `MIN_SLEEP`: Minimum sleep time between runs in seconds (default: 1)
- `MAX_SLEEP`: Maximum sleep time between runs in seconds (default: 3)
- `TEST_QUERIES`: List of test queries to use for the agent

You can also set these values using environment variables:
- `MAX_TEST_RUNS`: Number of test runs
- `DEBUG_MODE`: Set to '1' for debug mode

### Logs

The simulator logs results to the `tests/simulation_logs` directory:

- Individual run logs: `<timestamp>_<session_id>.json`
- Summary file: `summary_<timestamp>.json`

## Analyzing Results

To analyze the results of a stress test run:

```bash
python tests/analyze_results.py
```

This will:

1. Find the latest summary file
2. Analyze the results and print statistics
3. Generate charts (requires matplotlib)
4. Create an HTML report

You can specify a specific summary file:

```bash
python tests/analyze_results.py --summary tests/simulation_logs/summary_20230101_123456.json
```

## Reports

The analyzer generates the following reports:

- `tests/simulation_logs/stress_test_report.html`: HTML report with summary statistics and charts
- `tests/simulation_logs/execution_time_histogram.png`: Histogram of execution times
- `tests/simulation_logs/success_rate_pie.png`: Pie chart of success vs. failure rate
- `tests/simulation_logs/query_success_rates.png`: Bar chart of success rates by query 