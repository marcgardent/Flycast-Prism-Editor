#!/usr/bin/env python3
import os
import yaml

def sync_requirements():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(script_dir))
    env_file = os.path.join(root_dir, "environment.yml")
    req_file = os.path.join(script_dir, "requirements.txt")

    if not os.path.exists(env_file):
        print(f"Error: {env_file} not found")
        return

    with open(env_file, "r") as f:
        data = yaml.safe_load(f)

    if not data or "dependencies" not in data:
        print("Error: No dependencies found in environment.yml")
        return

    requirements = []
    
    for dep in data["dependencies"]:
        if isinstance(dep, str):
            # Conda dependency (e.g. "numpy", "python=3.10", "tk=*=xft_*")
            # Skip python, pip and conda-specific build tags
            if any(dep.startswith(x) for x in ["python", "pip", "tk="]):
                continue
            
            # Convert conda versioning '=' to pip versioning '=='
            if "=" in dep and not any(op in dep for op in ["==", ">=", "<=", ">", "<"]):
                dep = dep.replace("=", "==")
            
            requirements.append(dep)
            
        elif isinstance(dep, dict) and "pip" in dep:
            # Pip dependencies
            for pip_dep in dep["pip"]:
                requirements.append(pip_dep)

    # Unique and sorted
    requirements = sorted(list(set(requirements)))

    print(f"Syncing {len(requirements)} dependencies to {req_file}")
    with open(req_file, "w") as f:
        for req in requirements:
            f.write(f"{req}\n")

if __name__ == "__main__":
    sync_requirements()
