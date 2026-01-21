#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migrate existing TOML files to new _meta structure
Moves top-level 'name' and 'prompt' fields into [_meta] section
"""

import os
import toml
from pathlib import Path


def migrate_toml_file(file_path: str) -> bool:
    """
    Migrate a single TOML file to new structure
    
    Returns:
        True if file was modified, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = toml.load(f)
        
        # Check if migration is needed
        has_top_level_name = "name" in data and not isinstance(data.get("name"), dict)
        has_top_level_prompt = "prompt" in data and not isinstance(data.get("prompt"), dict)
        
        if not has_top_level_name and not has_top_level_prompt:
            # Already migrated or no migration needed
            return False
        
        # Create _meta section if it doesn't exist
        if "_meta" not in data:
            data["_meta"] = {}
        
        # Move name and prompt to _meta
        modified = False
        if has_top_level_name:
            data["_meta"]["name"] = data.pop("name")
            modified = True
            print(f"  Moved 'name' to _meta")
        
        if has_top_level_prompt:
            data["_meta"]["prompt"] = data.pop("prompt")
            modified = True
            print(f"  Moved 'prompt' to _meta")
        
        if modified:
            # Write back the modified file
            with open(file_path, 'w', encoding='utf-8') as f:
                toml.dump(data, f)
            return True
        
        return False
        
    except Exception as e:
        print(f"  ERROR: Failed to migrate {file_path}: {e}")
        return False


def migrate_all_toml_files(data_dir: str = "data"):
    """
    Migrate all TOML files in the data directory
    """
    data_path = Path(data_dir)
    if not data_path.exists():
        print(f"Data directory '{data_dir}' not found")
        return
    
    toml_files = list(data_path.glob("*.toml"))
    print(f"Found {len(toml_files)} TOML files to check")
    print()
    
    migrated_count = 0
    for toml_file in sorted(toml_files):
        print(f"Processing: {toml_file.name}")
        if migrate_toml_file(str(toml_file)):
            migrated_count += 1
            print(f"  ✓ Migrated")
        else:
            print(f"  - No migration needed")
        print()
    
    print(f"Migration complete: {migrated_count}/{len(toml_files)} files migrated")


if __name__ == "__main__":
    import sys
    
    # Get data directory from command line or use default
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    
    print("=" * 60)
    print("TOML Structure Migration Script")
    print("Moving 'name' and 'prompt' fields to [_meta] section")
    print("=" * 60)
    print()
    
    migrate_all_toml_files(data_dir)
