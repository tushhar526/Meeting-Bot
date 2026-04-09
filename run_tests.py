#!/usr/bin/env python3
"""
Test runner script for Meeting Bot
Usage: python run_tests.py [options]
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd):
    """Run a command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print("ERROR:", e.stdout)
        print("STDERR:", e.stderr)
        return False


def install_test_dependencies():
    """Install test dependencies"""
    print("Installing test dependencies...")
    return run_command("pip install -r requirements-test.txt")


def run_all_tests(coverage=False, verbose=False, marker=None):
    """Run all tests"""
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=app", "--cov-report=html", "--cov-report=term"])
    
    if marker:
        cmd.extend(["-m", marker])
    
    cmd.append("tests/")
    
    return run_command(" ".join(cmd))


def run_specific_test(test_path, coverage=False, verbose=False):
    """Run a specific test file"""
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=app", "--cov-report=html", "--cov-report=term"])
    
    cmd.append(test_path)
    
    return run_command(" ".join(cmd))


def run_tests_by_category(category, coverage=False, verbose=False):
    """Run tests by category"""
    markers = {
        "models": "models",
        "services": "services", 
        "controllers": "controllers",
        "routes": "routes",
        "logic": "logic",
        "helpers": "helpers",
        "auth": "auth",
        "unit": "unit",
        "integration": "integration"
    }
    
    marker = markers.get(category.lower())
    if not marker:
        print(f"Unknown category: {category}")
        print(f"Available categories: {', '.join(markers.keys())}")
        return False
    
    return run_all_tests(coverage=coverage, verbose=verbose, marker=marker)


def main():
    parser = argparse.ArgumentParser(description="Meeting Bot Test Runner")
    parser.add_argument("--install", action="store_true", help="Install test dependencies")
    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--test", "-t", help="Run specific test file")
    parser.add_argument("--category", "-c", help="Run tests by category")
    parser.add_argument("--marker", "-m", help="Run tests with specific pytest marker")
    
    args = parser.parse_args()
    
    # Install dependencies if requested
    if args.install:
        if not install_test_dependencies():
            sys.exit(1)
        print("Test dependencies installed successfully!")
        return
    
    # Check if tests directory exists
    if not Path("tests").exists():
        print("Tests directory not found!")
        print("Make sure you're running this from the project root directory.")
        sys.exit(1)
    
    # Run tests based on arguments
    success = True
    
    if args.test:
        success = run_specific_test(args.test, args.coverage, args.verbose)
    elif args.category:
        success = run_tests_by_category(args.category, args.coverage, args.verbose)
    else:
        success = run_all_tests(args.coverage, args.verbose, args.marker)
    
    if success:
        print("\n✅ All tests passed!")
        if args.coverage:
            print("📊 Coverage report generated in htmlcov/index.html")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
