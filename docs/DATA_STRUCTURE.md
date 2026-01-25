# Data Structure Documentation

## Translation TOML File Structure

Each mod's translations are stored in a TOML file with the following structure:

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

- **raw**: Original English text from the mod
- **status**: Translation status
  - `normal`: Active translation
  - `old`: The mod retains this key value in older versions.
  - `abandon`: Abandoned/unused
- **new**: Updated text that triggers retranslation (removed after translation completes)
- **prompt**: Entry-specific translation hints
- **Language codes**: Translations for each supported language

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
```

### Translation Workflow

1. **New mod added**: Only `new` field exists, no `raw` field yet
2. **First translation**: Script translates `new` to all languages
3. **After translation**: `raw` is set to `new` value, `new` field is removed
4. **Update detected**: If text changes, `new` field is added again
5. **Retranslation**: Script retranslates for all languages, updates `raw`, removes `new`

### Glossary Features

The glossary system supports:

- **Global glossary**: `glossary.toml` at repository root
- **Mod-local glossary**: `[_meta.glossary]` in mod TOML file
- **Priority**: Local glossary overrides global glossary
- **Partial languages**: Only define languages you need
- **Fuzzy matching**: For terms 10+ characters with configurable tolerance
- **Skip hints**: Prevent hints for specific terms (proper names)
- **Language priority**: Hints show only first available language

See [README.md](../README.md) for more details on glossary features.
