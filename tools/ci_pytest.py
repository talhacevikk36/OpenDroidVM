"""Runs pytest; on failure also emits GitHub annotations so the error is visible in the API/UI summary."""
import subprocess
import sys

r = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests", "--tb=short", "-p", "no:cacheprovider"],
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
print(r.stdout)
if r.returncode:
    for line in r.stdout.splitlines()[-60:]:
        if line.strip():
            print("::error::" + line.replace("%", "%25").replace("\r", "")[:280])
sys.exit(r.returncode)
