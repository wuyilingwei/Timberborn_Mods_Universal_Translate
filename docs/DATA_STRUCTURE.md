# Data Structure Documentation

## Translation TOML File Structure

Each mod's translations are stored in a TOML file with the following structure:

If you don't know what a TOML file is, please take one minute to read this document: https://toml.io

### Basic Structure

```toml
# Metadata section for mod configuration
[_meta]
name = "Mod Name"
prompt = "Optional translation hints"

# Mod-local glossary
[_meta.glossary."CustomTerm"]
zhCN = "自定义术语"
zhTW = "自訂術語"

["Translation.Entry.Key"]
raw = "Original English text"
status = "normal"  # normal / old / abandon
new = "Updated text"  # If present, triggers retranslation
prompt = "Entry-specific translation hints"
enUS = "English translation"
zhCN = "Chinese (Simplified) translation"
zhTW = "Chinese (Traditional) translation"
ruRU = "Russian translation"
jaJP = "Japanese translation"
frFR = "French translation"
deDE = "German translation"
plPL = "Polish translation"
ptBR = "Portuguese (Brazil) translation"
koKR = "Korean translation"
```

### Field Descriptions

#### `[_meta]` Section

The `_meta` section contains metadata that doesn't conflict with translation keys:

- **name**: Mod name (required)
- **prompt**: Optional translation hints for the mod
- **glossary**: Mod-specific glossary entries

##### Glossary Structure

```toml
[_meta.glossary."Term"]
zhCN = "翻译"
zhTW = "翻譯"
# Only define languages you need

# Advanced format with options
[_meta.glossary."AdvancedTerm"]
skip_hints = true  # Don't show hints for missing translations
fuzzy_tolerance = 3  # Custom tolerance for fuzzy matching
zhCN = "高级术语"
```

#### Translation Entry Fields

Each translation entry uses a key in the format `["Category.Item.Field"]`:

- **raw**: Original text (Most of time, it's English) from the mod
- **status**: Translation status
  - `normal`: Active translation
  - `old`: The mod retains this key value in older versions.
  - `abandon`: Abandoned/unused
- **new**: Updated text that triggers retranslation (removed after translation completes)
- **copy**: Boolean flag (default: false) - If true, treats this as a symbolic field and copies the source text directly without translation
- **prompt**: Entry-specific translation hints
- **Language codes**: Translations for each supported language

Hint: Most of time, you only need change prompt and translations.

### Supported Languages

- `enUS`: English (US)
- `zhCN`: Chinese (Simplified)
- `zhTW`: Chinese (Traditional)
- `ruRU`: Russian
- `jaJP`: Japanese
- `frFR`: French
- `deDE`: German
- `plPL`: Polish
- `ptBR`: Portuguese (Brazil)
- `koKR`: Korean

### Example: Complete Mod File

```toml
name = "Building Expansion Mod"
prompt = "Building names and descriptions"

[_meta]
[_meta.glossary."CustomBuilding"]
zhCN = "自定义建筑"
zhTW = "自訂建築"

["Building.CustomBuilding.DisplayName"]
raw = "Custom Building"
status = "normal"
enUS = "Custom Building"
zhCN = "自定义建筑"
zhTW = "自訂建築"
ruRU = "Специальное здание"
jaJP = "カスタムビルディング"
frFR = "Bâtiment personnalisé"
deDE = "Benutzerdefiniertes Gebäude"
plPL = "Niestandardowy budynek"
ptBR = "Edifício Personalizado"
koKR = "사용자 지정 건물"

["Building.CustomBuilding.Description"]
raw = "A building with special features"
status = "normal"
new = "A building with amazing features"  # Triggers retranslation
prompt = "Keep translation concise"
enUS = "A building with special features"
zhCN = "具有特殊功能的建筑"
# ... other languages

["Building.CustomBuilding.Id"]
raw = "CustomBuilding_001"
status = "normal"
copy = true  # Symbolic field - copy directly without translation
enUS = "CustomBuilding_001"
zhCN = "CustomBuilding_001"  # Same as source
# ... other languages (all identical)
```

### Translation Workflow

1. **New mod added**: Only `new` field exists, no `raw` field yet
2. **First translation**: Script translates `new` to all languages
3. **After translation**: `raw` is set to `new` value, `new` field is removed
4. **Update detected**: If text changes, `new` field is added again
5. **Retranslation**: Script retranslates for all languages, updates `raw`, removes `new`

### Glossary Features

The glossary system supports:

- **Global glossary**: `data/_glossary.toml` in data directory
- **Mod-local glossary**: `[_meta.glossary]` in mod TOML file
- **Priority**: Local glossary overrides global glossary
- **Partial languages**: Only define languages you need
- **Fuzzy matching**: For terms 10+ characters with configurable tolerance
- **Skip hints**: Prevent hints for specific terms (proper names)
- **Language priority**: Hints show only first available language

See [README.md](../README.md) for more details on glossary features.


## Global Glossary System

The global glossary (`data/_glossary.toml`) provides translations for commonly used game-specific terms that appear across multiple mods. This reduces translation workload and ensures consistency.

### Key Features

#### Case-Insensitive Matching

The glossary system uses **case-insensitive matching**, meaning you only need to define one entry per term:

```toml
# This single entry matches all case variations:
["tank"]
zhCN = "水罐"
zhTW = "水罐"

# Matches: "tank", "Tank", "TANK", "tAnK", etc.
```

**Benefits:**
- No need for duplicate entries like `["tank"]` and `["Tank"]
- Simplified maintenance
- Consistent translations across case variations

#### Fuzzy Matching

For terms with 10+ characters, the system allows character differences (default: 2 characters):

```toml
["Construction"]
zhCN = "建设"
# Also matches: "Consruction" (missing 't'), "Constructoin" (transposed 'io')

# Custom tolerance
["Infrastructure"]
fuzzy_tolerance = 3
zhCN = "基础设施"
# Allows up to 3 character differences
```

#### Special Options

```toml
# Skip translation hints (for proper names)
["Timberborn"]
skip_hints = true
zhCN = "海狸浮生记"
zhTW = "海狸浮生記"

# Custom fuzzy tolerance
["VeryLongTermName"]
fuzzy_tolerance = 4
zhCN = "很长的术语名称"

# New format with explicit structure (optional)
["ModernTerm"]
skip_hints = false
fuzzy_tolerance = 2
translations = { zhCN = "现代术语", zhTW = "現代術語" }
```

### Priority System

1. **Mod-local glossary** (`[_meta.glossary]`) takes highest priority
2. **Global glossary** (`data/_glossary.toml`) provides fallback translations
3. **Translation hints** show available alternatives when target language is missing

### Usage Examples

#### Before Translation (Source Text)
```
"The Tank needs maintenance"
```

#### After Glossary Processing
```
"The 水罐 needs maintenance"  # zhCN
"The 水罐 needs maintenance"  # zhTW
```

#### Translation Hints
When a glossary term exists but lacks the target language:
```
Term "pump" in zhCN: 水泵
```
