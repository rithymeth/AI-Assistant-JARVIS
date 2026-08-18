import subprocess

from tools.file_system import WORKSPACE_DIR

TIMEOUT_SECONDS = 30


def run_command(command: str) -> dict:
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(WORKSPACE_DIR),
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        return {
            "stdout": result.stdout[-5000:],
            "stderr": result.stderr[-5000:],
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"Command timed out after {TIMEOUT_SECONDS}s", "returncode": -1}
