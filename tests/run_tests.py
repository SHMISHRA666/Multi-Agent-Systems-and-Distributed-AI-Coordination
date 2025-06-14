import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    print(f"Python path: {sys.path}")
    print("Running HITL Tests...")
    print("=" * 50)
    
    import pytest
    pytest.main(["-v", "-s", "tests/test_hitl.py"]) 