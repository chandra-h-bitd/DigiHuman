import subprocess
import sys
from pathlib import Path


def _read_requirements(requirements_path: Path) -> list[str]:
    requirements: list[str] = []
    for raw_line in requirements_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        requirements.append(line)
    return requirements


def _install(requirement: str) -> tuple[bool, str]:
    process = subprocess.run(
        [sys.executable, "-m", "pip", "install", requirement],
        capture_output=True,
        text=True,
    )
    if process.returncode == 0:
        return True, process.stdout.strip()

    error_output = process.stderr.strip() or process.stdout.strip() or "Unknown error"
    return False, error_output


def main() -> int:
    requirements_path = Path(__file__).with_name("requirements.txt")
    if not requirements_path.exists():
        print(f"[ERROR] Cannot find {requirements_path}")
        return 1

    requirements = _read_requirements(requirements_path)
    successes: list[str] = []
    failures: list[tuple[str, str]] = []

    print("[INFO] Installing backend dependencies individually...\n")
    for requirement in requirements:
        print(f"  -> {requirement}")
        ok, message = _install(requirement)
        if ok:
            print("     [OK] Installed")
            successes.append(requirement)
        else:
            print("     [FAIL] Installation failed")
            print(f"            Reason: {message.splitlines()[-1]}")
            failures.append((requirement, message))
        print()

    print("========================================")
    print("Dependency installation summary")
    print("========================================\n")

    if successes:
        print("[SUCCESS]")
        for requirement in successes:
            print(f"  - {requirement}")
        print()

    if failures:
        print("[FAILED]")
        for requirement, message in failures:
            reason = message.splitlines()[-1]
            print(f"  - {requirement}: {reason}")
        print()
        print("[ACTION REQUIRED] Resolve the failures above before running python -m app.main")
        return 1

    print("[OK] All backend dependencies installed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

