import subprocess
import glob
import sys

tests = glob.glob('test_*.py')
passed = 0
failed = 0
skipped = 0
total = len(tests)

for test in tests:
    print(f"Running {test}...")
    res = subprocess.run([sys.executable, test], capture_output=True, text=True)
    if res.returncode == 0:
        passed += 1
        print(f"  PASS")
    else:
        failed += 1
        print(f"  FAIL")
        print(res.stderr)
        print(res.stdout)

print(f"\nTOTAL TESTS: {total}")
print(f"PASSED: {passed}")
print(f"FAILED: {failed}")
print(f"SKIPPED: {skipped}")
