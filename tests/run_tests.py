"""
Standard Library Test Runner for MALA Framework
===============================================
Runs the unit tests in tests/test_mala.py without relying on external dependencies like pytest.
Provides a detailed academic report of all mathematical and system assertions.
"""

import sys
import os
import traceback
import time

# Ensure repository root is in sys.path so it runs seamlessly from anywhere
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def run_suite():
    print("=" * 80)
    print("  MALA FRAMEWORK MATHEMATICAL & SYSTEM TEST SUITE")
    print("  Standard Library Runner — Absolute Portability Mode")
    print("=" * 80 + "\n")

    # Import the tests
    try:
        from tests import test_mala
    except ImportError:
        try:
            import test_mala
        except ImportError as e:
            print(f"Error importing test suite: {e}")
            sys.exit(1)

    # Find all test functions
    test_functions = [
        (name, getattr(test_mala, name))
        for name in dir(test_mala)
        if name.startswith("test_") and callable(getattr(test_mala, name))
    ]

    total_tests = len(test_functions)
    passed_tests = 0
    failures = []

    print(f"Discovered {total_tests} test suites verifying MALA paper formulations:\n")

    start_time = time.time()
    for name, func in test_functions:
        print(f"Running {name:<40} ... ", end="", flush=True)
        try:
            func()
            print("\033[92mPASSED\033[0m")
            passed_tests += 1
        except Exception as e:
            print("\033[91mFAILED\033[0m")
            failures.append((name, e, traceback.format_exc()))

    elapsed_time = time.time() - start_time

    print("\n" + "=" * 80)
    print("  TEST SUITE RESULTS SUMMARY")
    print("=" * 80)
    print(f"  Tests Discovered : {total_tests}")
    print(f"  Tests Passed     : {passed_tests}")
    print(f"  Tests Failed     : {len(failures)}")
    print(f"  Elapsed Time     : {elapsed_time:.3f} seconds")
    print("=" * 80 + "\n")

    if failures:
        print("Detailed failure logs:")
        for name, err, tb in failures:
            print("-" * 80)
            print(f"Failure in: {name}")
            print(f"Error: {err}")
            print(tb)
        sys.exit(1)
    else:
        print("All tests passed successfully! All mathematical and system formulations match the specifications.")
        sys.exit(0)

if __name__ == "__main__":
    # If the user runs this file directly, and pytest is not installed,
    # let's mock the 'pytest' module so that importing test_mala works!
    class PytestMock:
        class ApproxMock:
            def __init__(self, expected, abs=None):
                self.expected = expected
                self.abs = abs
            def __eq__(self, other):
                if self.abs is not None:
                    return abs(self.expected - other) <= self.abs
                return abs(self.expected - other) <= 1e-6
        def approx(self, expected, abs=None):
            return self.ApproxMock(expected, abs)
    
    # Inject mock pytest into sys.modules before importing tests
    sys.modules['pytest'] = PytestMock()
    
    run_suite()
