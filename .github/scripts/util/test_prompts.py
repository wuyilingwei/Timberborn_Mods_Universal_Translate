#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: (ALE-1.1 AND GPL-3.0-only)
# Copyright (c) 2022-2025 wuyilingwei
#
# This file is licensed under the ANTI-LABOR EXPLOITATION LICENSE 1.1
# in combination with GNU General Public License v3.0.
# See .github/LICENSE for full license text.
"""
Test script for translation prompt building
"""

import sys
import os

# Add the scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from translate_mods import build_translation_prompt


def test_prompt_building():
    """Test that prompts are built correctly with various field combinations"""
    
    print("Test 1: Minimal prompt (only key and new text)")
    print("-" * 60)
    sys_prompt, user_prompt = build_translation_prompt(
        key="TestMod.Item.Name",
        new_text="New Item",
        mod_name="Test Mod",
        target_language="zhCN"
    )
    print(f"System: {sys_prompt}")
    print(f"User: {user_prompt}")
    print()
    
    print("Test 2: Full context prompt")
    print("-" * 60)
    sys_prompt, user_prompt = build_translation_prompt(
        key="TestMod.Building.Description",
        new_text="A brand new building with amazing features",
        mod_name="Building Expansion",
        target_language="jaJP",
        raw="An old building description",
        current_translation="古い建物の説明",
        field_prompt="These are building descriptions",
        specific_prompt="Keep translation formal"
    )
    print(f"System: {sys_prompt}")
    print(f"User: {user_prompt}")
    print()
    
    print("Test 3: Partial context (no current translation)")
    print("-" * 60)
    sys_prompt, user_prompt = build_translation_prompt(
        key="NewMod.Feature.Title",
        new_text="Advanced Feature",
        mod_name="New Mod",
        target_language="frFR",
        raw="Basic Feature",
        field_prompt="UI elements"
    )
    print(f"System: {sys_prompt}")
    print(f"User: {user_prompt}")
    print()
    
    print("Test 4: With specific prompt only")
    print("-" * 60)
    sys_prompt, user_prompt = build_translation_prompt(
        key="AnotherMod.Message.Alert",
        new_text="Critical system failure!",
        mod_name="System Mod",
        target_language="deDE",
        specific_prompt="This is an error message, keep it concise"
    )
    print(f"System: {sys_prompt}")
    print(f"User: {user_prompt}")
    print()
    
    print("All tests completed!")


if __name__ == "__main__":
    test_prompt_building()
