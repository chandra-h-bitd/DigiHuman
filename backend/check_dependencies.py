"""
Check which dependencies from requirements.txt can be installed
"""
import subprocess
import sys
import re

def parse_requirements(file_path):
    """Parse requirements.txt file"""
    requirements = []
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if line and not line.startswith('#'):
                # Extract package name (before >=, ==, etc.)
                match = re.match(r'^([a-zA-Z0-9\-_]+)', line)
                if match:
                    package_name = match.group(1)
                    requirements.append((package_name, line))
    return requirements

def check_package(package_name, spec):
    """Check if a package can be installed"""
    try:
        # Try to import the package first (if already installed)
        try:
            __import__(package_name.replace('-', '_'))
            return "INSTALLED", None
        except ImportError:
            pass
        
        # Check if package exists on PyPI
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'index', 'versions', package_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return "AVAILABLE", None
        else:
            # Try alternative method
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'search', package_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return "AVAILABLE", None
            else:
                return "NOT_FOUND", result.stderr
                
    except subprocess.TimeoutExpired:
        return "TIMEOUT", "Request timed out"
    except FileNotFoundError:
        return "ERROR", "pip not found"
    except Exception as e:
        return "ERROR", str(e)

def check_install(package_name, spec):
    """Try to install a package (dry-run)"""
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '--dry-run', spec],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return True, None
        else:
            error_msg = result.stderr or result.stdout
            return False, error_msg
    except subprocess.TimeoutExpired:
        return False, "Installation check timed out"
    except Exception as e:
        return False, str(e)

def main():
    """Main function to check dependencies"""
    requirements_file = "requirements.txt"
    
    print("=" * 70)
    print("Checking Dependencies from requirements.txt")
    print("=" * 70)
    print()
    
    try:
        requirements = parse_requirements(requirements_file)
    except FileNotFoundError:
        print(f"[ERROR] {requirements_file} not found!")
        return 1
    
    print(f"Found {len(requirements)} packages to check\n")
    
    results = {
        "installed": [],
        "available": [],
        "failed": [],
        "errors": []
    }
    
    for package_name, spec in requirements:
        print(f"Checking: {package_name}...", end=" ", flush=True)
        
        # First check if already installed
        try:
            __import__(package_name.replace('-', '_').replace('_', ''))
            print("[ALREADY INSTALLED]")
            results["installed"].append((package_name, spec))
            continue
        except ImportError:
            pass
        
        # Try dry-run installation
        can_install, error = check_install(package_name, spec)
        
        if can_install:
            print("[OK - Can install]")
            results["available"].append((package_name, spec))
        else:
            print("[FAILED]")
            results["failed"].append((package_name, spec, error))
    
    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Already Installed: {len(results['installed'])}")
    print(f"Can Install: {len(results['available'])}")
    print(f"Failed: {len(results['failed'])}")
    print()
    
    if results["installed"]:
        print("Already Installed Packages:")
        for package_name, spec in results["installed"]:
            print(f"  - {package_name}")
        print()
    
    if results["available"]:
        print("Packages Available for Installation:")
        for package_name, spec in results["available"]:
            print(f"  - {package_name}")
        print()
    
    if results["failed"]:
        print("Packages That Failed:")
        for package_name, spec, error in results["failed"]:
            print(f"  - {package_name}")
            if error:
                error_lines = error.split('\n')[:3]  # First 3 lines
                for line in error_lines:
                    if line.strip():
                        print(f"    Error: {line.strip()}")
        print()
    
    # Try actual installation check
    print("=" * 70)
    print("Testing Installation (this may take a while...)")
    print("=" * 70)
    print()
    
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '--dry-run', '-r', requirements_file],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("[OK] All packages can be installed!")
            print("\nOutput:")
            print(result.stdout)
        else:
            print("[FAILED] Some packages cannot be installed")
            print("\nErrors:")
            print(result.stderr)
            print("\nOutput:")
            print(result.stdout)
    except subprocess.TimeoutExpired:
        print("[TIMEOUT] Installation check took too long")
    except Exception as e:
        print(f"[ERROR] {e}")
    
    return 0 if len(results["failed"]) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())

