#!/usr/bin/env python3
"""
Script to validate GitHub Actions workflow files.
"""

import yaml
import sys
from pathlib import Path

def validate_yaml_file(filepath: Path) -> bool:
    """Validate that a YAML file is well-formed."""
    try:
        with open(filepath, 'r') as f:
            yaml.safe_load(f)
        print(f"✅ {filepath.name} is valid YAML")
        return True
    except yaml.YAMLError as e:
        print(f"❌ {filepath.name} has YAML syntax error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading {filepath.name}: {e}")
        return False

def validate_workflow_structure(filepath: Path) -> bool:
    """Validate GitHub Actions workflow structure."""
    try:
        with open(filepath, 'r') as f:
            workflow = yaml.safe_load(f)
        
        # Check required top-level keys
        # Note: 'on' might be parsed as boolean True in YAML
        required_keys = ['name', 'jobs']
        trigger_key = 'on' in workflow or True in workflow
        
        missing_keys = [key for key in required_keys if key not in workflow]
        if not trigger_key:
            missing_keys.append('on')
        
        if missing_keys:
            print(f"❌ {filepath.name} missing required keys: {missing_keys}")
            return False
        
        # Check that jobs is not empty
        if not workflow['jobs']:
            print(f"❌ {filepath.name} has no jobs defined")
            return False
        
        # Check each job has required structure
        for job_name, job_config in workflow['jobs'].items():
            if 'runs-on' not in job_config:
                print(f"❌ {filepath.name} job '{job_name}' missing 'runs-on'")
                return False
            
            if 'steps' not in job_config:
                print(f"❌ {filepath.name} job '{job_name}' missing 'steps'")
                return False
        
        print(f"✅ {filepath.name} has valid workflow structure")
        return True
        
    except Exception as e:
        print(f"❌ Error validating {filepath.name} structure: {e}")
        return False

def main():
    """Validate all workflow files."""
    workflows_dir = Path(__file__).parent / 'workflows'
    
    if not workflows_dir.exists():
        print("❌ No workflows directory found")
        sys.exit(1)
    
    yaml_files = list(workflows_dir.glob('*.yml')) + list(workflows_dir.glob('*.yaml'))
    
    if not yaml_files:
        print("❌ No workflow files found")
        sys.exit(1)
    
    print(f"🔍 Validating {len(yaml_files)} workflow file(s)...")
    
    all_valid = True
    
    for filepath in yaml_files:
        print(f"\n📄 Validating {filepath.name}...")
        
        # Validate YAML syntax
        if not validate_yaml_file(filepath):
            all_valid = False
            continue
        
        # Validate workflow structure
        if not validate_workflow_structure(filepath):
            all_valid = False
            continue
    
    print(f"\n{'✅ All workflows are valid!' if all_valid else '❌ Some workflows have issues'}")
    
    if not all_valid:
        sys.exit(1)

if __name__ == "__main__":
    main()