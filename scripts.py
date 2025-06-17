"""
Build and development scripts for the project.
"""
import subprocess
import sys


def run_command(cmd: list[str]) -> int:
    """Run a command and return its exit code."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def check():
    """Run code quality checks."""
    commands = [
        ["ruff", "check", "src", "tests"],
        ["black", "--check", "src", "tests"],
        ["mypy", "src"],
    ]
    
    for cmd in commands:
        if run_command(cmd) != 0:
            print(f"❌ Check failed: {' '.join(cmd)}")
            sys.exit(1)
    
    print("✅ All checks passed!")


def format():
    """Format code with black and ruff."""
    commands = [
        ["black", "src", "tests"],
        ["ruff", "check", "--fix", "src", "tests"],
        ["ruff", "format", "src", "tests"],
    ]
    
    for cmd in commands:
        run_command(cmd)
    
    print("✅ Code formatted!")


def test():
    """Run tests with pytest."""
    sys.exit(run_command(["pytest"]))


def build():
    """Run all checks and tests (like npm run build)."""
    print("🔨 Building project...")
    
    # Run linting and type checking
    commands = [
        ["ruff", "check", "src", "tests"],
        ["mypy", "src"],
    ]
    
    for cmd in commands:
        if run_command(cmd) != 0:
            print(f"❌ Build failed: {' '.join(cmd)}")
            sys.exit(1)
    
    # Import check
    print("Checking imports...")
    import_check = subprocess.run(
        [sys.executable, "-c", "from src.main import app; print('✓ Import check passed')"],
        capture_output=True,
        text=True
    )
    if import_check.returncode != 0:
        print(f"❌ Import check failed: {import_check.stderr}")
        sys.exit(1)
    print(import_check.stdout.strip())
    
    # Run tests
    if run_command(["pytest", "tests/"]) != 0:
        print("❌ Tests failed")
        sys.exit(1)
    
    print("✅ Build successful!")


if __name__ == "__main__":
    # For testing individual functions
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["check", "format", "test", "build"])
    args = parser.parse_args()
    
    if args.command == "check":
        check()
    elif args.command == "format":
        format()
    elif args.command == "test":
        test()
    elif args.command == "build":
        build()