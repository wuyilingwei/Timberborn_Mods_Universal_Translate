#!/bin/bash
# Example script to run the translation system
# This demonstrates how to use the translation automation

# Set your API token (or export it as an environment variable)
# export LLM_TOKEN="your-api-token-here"
# or
# export OPENAI_API_KEY="your-api-token-here"

# Basic usage - processes all TOML files in data/ directory
python .github/scripts/translate_mods.py

# Dry run to test without making changes
# python .github/scripts/translate_mods.py --dry-run --verbose

# Custom configuration
# python .github/scripts/translate_mods.py \
#   --config .github/config/translate.toml \
#   --data-dir data \
#   --lang-file info/languages.txt \
#   --verbose
