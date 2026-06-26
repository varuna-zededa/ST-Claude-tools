#!/usr/bin/env python3
"""
Test runner for MCP module tests.
Run all tests with proper configuration.
"""
import subprocess
import sys
import os
from pathlib import Path

def run_tests():
    """Run all tests with pytest."""
    # Change to the mcp directory
    mcp_dir = Path(__file__).parent
    os.chdir(mcp_dir)
    
    # Run pytest with verbose output
    cmd = [
        sys.executable, "-m", "pytest",
        "-v",
        "--tb=short",
        "--strict-markers",
        "test_*.py"
    ]
    
    print("Running MCP module tests...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)
    
    result = subprocess.run(cmd, capture_output=False)
    
    print("-" * 50)
    if result.returncode == 0:
        print("All tests passed!")
    else:
        print("Some tests failed!")
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(run_tests())
