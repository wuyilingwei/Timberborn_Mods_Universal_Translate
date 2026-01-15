# Translation Automation System

This system provides automated translation for Timberborn mod localization files using OpenAI-compatible LLM APIs.

## Overview

The translation system processes TOML files in the `data/` directory and automatically translates entries that have a `new` field, indicating that the source text has been updated and needs retranslation.

## Features

- **Multi-threaded Translation**: Process multiple mods simultaneously for faster translation
- **Rate Limiting**: Built-in rate limiter prevents API rejection by controlling request rate
- **Smart Context**: Provides comprehensive context to the LLM including:
  - Original text (if changed)
  - Current translation (for reference)
  - Field-level hints
  - Entry-specific notes
- **Automatic Field Management**: Removes `new` field after successful translation and updates `raw` field

## Configuration

Configuration is stored in `.github/config/translate.toml`:

```toml
[rate_limiter]
# Maximum requests per minute (RPM)
max_requests_per_minute = 10

# Number of concurrent translation threads
max_threads = 5

[llm]
# LLM model to use for translation
model = "gpt-4o-mini"

# API endpoint (OpenAI-compatible)
api_url = "https://api.openai.com/v1/chat/completions"

# Minimum text length to translate
min_length = 1

# Maximum text length to translate
max_length = 5000
```

## TOML File Format

Each TOML file in `data/` represents a mod with the following structure:

```toml
name = "Mod Name"  # Optional: mod name for better context
field_prompt = "Additional context about this mod"  # Optional: extra hints for translation

["ModAuthor.ModName.EntryKey"]
raw = "Original English Text"  # The current source text
new = "Updated English Text"   # If present, this entry needs translation
prompt = "Specific translation note"  # Optional: entry-specific instructions
enUS = "Original English Text"
zhCN = "简体中文翻译"
zhTW = "繁體中文翻譯"
ruRU = "Русский перевод"
jaJP = "日本語訳"
frFR = "Traduction française"
deDE = "Deutsche Übersetzung"
plPL = "Polskie tłumaczenie"
ptBR = "Tradução em português"
```

### Field Descriptions

- `name`: Optional mod name for context
- `field_prompt`: Optional global hint for all translations in this mod
- `raw`: The current/old source text
- `new`: When present, indicates the source text has been updated and all translations need to be refreshed
- `prompt`: Optional entry-specific translation instructions
- Language codes: Actual translations for each supported language

### Translation Process

When a `new` field is present:
1. The system translates the new text to all target languages
2. Upon successful translation:
   - Updates `raw` field with the value from `new`
   - Updates all language fields with new translations
   - Removes the `new` field

## Usage

### Prerequisites

Install required Python packages:

```bash
pip install -r requirements.txt
```

### API Token

The system requires an OpenAI-compatible API token. Provide it in one of these ways:

1. **User-defined secrets module**: Create a `secrets.py` file with `LLM_TOKEN` variable (note: this is a user-defined module, not Python's built-in cryptographic secrets module)
2. **Environment variable**: Set `LLM_TOKEN` or `OPENAI_API_KEY`
3. **Command line**: Use `--api-token` argument

### Running the Translator

Basic usage:

```bash
python .github/scripts/translate_mods.py
```

With custom settings:

```bash
python .github/scripts/translate_mods.py \
  --config .github/config/translate.toml \
  --data-dir data \
  --lang-file info/languages.txt \
  --api-token YOUR_API_TOKEN \
  --verbose
```

Dry run (no changes made):

```bash
python .github/scripts/translate_mods.py --dry-run --verbose
```

### Command Line Options

- `--config`: Path to configuration file (default: `.github/config/translate.toml`)
- `--data-dir`: Directory containing TOML files (default: `data`)
- `--lang-file`: File containing target languages (default: `info/languages.txt`)
- `--api-token`: API token for LLM authentication
- `--dry-run`: Run without making changes (for testing)
- `--verbose`: Enable detailed logging

## Translation Prompts

The system constructs context-aware prompts for the LLM:

**System Prompt:**
```
You are a professional game translator specializing in "Timberborn" mod {mod_name}. 
Translate the given text to {target_language} and only return the translated text.
```

**User Prompt (dynamically built):**
```
Key name: {key} - New Text to Translate: "{new}" - Original Text (Old): "{raw}" - 
Current Translation: "{current_translation}" - Field Hint: {field_prompt} - 
Specific Note: {prompt}
```

Only fields that have values are included in the prompt to avoid confusion.

## Supported Languages

Languages are loaded from `info/languages.txt`:

- `enUS`: English (US)
- `zhCN`: Simplified Chinese
- `zhTW`: Traditional Chinese
- `ruRU`: Russian
- `jaJP`: Japanese
- `frFR`: French
- `deDE`: German
- `plPL`: Polish
- `ptBR`: Brazilian Portuguese

## Rate Limiting

The rate limiter ensures API requests stay within configured limits:

- Tracks request history within the time window
- Automatically sleeps when limit is reached
- Configurable as requests per second/minute/hour
- Format: `"num/unit"` (e.g., `"10/m"` for 10 per minute)

This prevents API rejection due to excessive requests while still allowing parallel processing.

## Multi-threading

The system can process multiple mods in parallel:

- Configure with `max_threads` in config file
- Each thread respects the global rate limiter
- Requests are queued when rate limit is reached
- Balances speed with API constraints

## Error Handling

The system handles various error conditions:

- **Connection failures**: Logged and skipped, translation continues
- **API errors**: Logged with details, entry remains untranslated
- **Malformed TOML**: File skipped, error logged
- **Missing translations**: Entry kept with `new` field for retry

## Examples

### Example 1: New mod entry

```toml
["NewMod.Building.Name"]
new = "Water Wheel"
```

After translation:
```toml
["NewMod.Building.Name"]
raw = "Water Wheel"
enUS = "Water Wheel"
zhCN = "水车"
# ... other languages
```

### Example 2: Updated entry

```toml
["ExistingMod.Item.Description"]
raw = "Old description"
new = "Updated description with new features"
enUS = "Old description"
zhCN = "旧描述"
```

After translation:
```toml
["ExistingMod.Item.Description"]
raw = "Updated description with new features"
enUS = "Updated description with new features"
zhCN = "更新的描述，包含新功能"
# ... other languages updated
```

### Example 3: Entry with context

```toml
name = "Building Mod"
field_prompt = "These are building names and descriptions"

["BuildingMod.Structure.Name"]
raw = "Old name"
new = "New structure name"
prompt = "This is a large industrial building"
enUS = "Old name"
zhCN = "旧名称"
```

The translator receives rich context for better translation quality.

## Troubleshooting

### No translations happening

- Check that TOML files have `new` fields
- Verify API token is set correctly
- Check logs for connection errors

### Rate limit errors

- Reduce `max_requests_per_minute` in config
- Reduce `max_threads` for fewer parallel requests

### Poor translation quality

- Add `field_prompt` to TOML for mod-level context
- Add `prompt` to specific entries for better hints
- Ensure `raw` field contains the old text for reference

## License

This translation system is part of the Timberborn Mods Universal Translate project.
