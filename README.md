# Timberborn Mods Universial Translate

![](info/thumbnail.png)

### **Get mod?**

#### Full Support:

 - [Download From Github Release](https://github.com/wuyilingwei/Timberborn_Mods_Universal_Translate/releases/latest)

 - [Subscribe On Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3346918947)

#### Other distribution:

 - [Download From Mod.io](https://mod.io/g/timberborn/m/mods-universal-translate)

## Join us

```
Video Games, our passion.
Creativity. Innovation.
Our part of life.
But what if the text doesn't speak your language?
No...I can't understand...

*UNKNOWN LANGUAGES*

Look Familiar?
Scenes like these are happening all over the internet, right now!
You could be next.
<- a exciting music ->
That is unless you make the most important decision of your life.
Prove to yourself that you have the dedication and skill to bridge language barriers.
Join...the Translators.
Become part of an elite force dedicated to expanding the modding universe.
See the world through new words.
And spread Each Idea across the globe.
Become a hero.
Become a legend.

BECOME A TRANSLATOR.
```

Want to contribute? See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for details on how to join and our translation rules.

## Documentation

- [Contributing Guide](docs/CONTRIBUTING.md) - How to join and contribution rules
- [Data Structure](docs/DATA_STRUCTURE.md) - TOML file structure and translation workflow

## Translation Features

### Glossary Support

The translation system supports both global and mod-local glossaries for consistent translation of key terms.

**Global Glossary (`glossary.toml`):**
- Provides direct mappings for common game-specific vocabulary like "Timberborn", "Beaver", "District", etc.
- Applied to all mods during translation
- Terms are replaced in the source text BEFORE LLM translation (preprocessing)
- Replacements are done from longest to shortest to avoid partial replacements

**Advanced Glossary Features:**
1. **Automatic Replacement**: Exact matches are replaced with translations before LLM
2. **Fuzzy Matching**: Terms with 10+ characters allow configurable character differences (default: 2, e.g., "SpecalResource" matches "SpecialResource")
3. **Hint Generation**: When a term has no translation for target language, provides reference from first available language in priority order
4. **Skip Hints Flag**: Prevent hints for specific terms (e.g., proper names that shouldn't show alternatives)
5. **Language Priority**: Hints show only the first available language from config order (e.g., if zhCN available, won't show zhTW)
6. **Configurable Fuzzy Tolerance**: Each term can have its own fuzzy matching tolerance

**Mod-Local Glossary:**
- Individual mods can define their own glossary terms in a `[_meta]` section
- Local glossary terms override global glossary (when there's a conflict)
- Supports partial language definitions (you don't need to define all languages)

**Example mod TOML structure with local glossary:**
```toml
name = "My Mod"
prompt = "Optional extra hints"  # No field_ prefix

# Metadata section for mod-specific configuration
[_meta]
# Optional: Override mod name if needed
# name = "Different Display Name"

# Mod-local glossary - overrides global glossary terms
[_meta.glossary."CustomTerm"]
zhCN = "自定义术语"
zhTW = "自訂術語"
# Only define the languages you need

# Advanced: Skip hints for proper names
[_meta.glossary."ProperName"]
skip_hints = true
translations = { zhCN = "专有名称" }

# Advanced: Custom fuzzy tolerance
[_meta.glossary."LongTermWithTypos"]
fuzzy_tolerance = 3  # Allow up to 3 character differences
zhCN = "容易拼错的长术语"

["ModEntry.Key"]
raw = "Some text with CustomTerm"
status = "normal"
# ... translations
```

**Global glossary entry example:**
```toml
["Timberborn"]
zhCN = "海狸浮生记"
zhTW = "海狸浮生記"
# ... other languages
```

**How It Works:**
1. Source text: `"Build Timberborn with Beaver"`
2. Exact matches replaced: `"Build 海狸浮生记 with 海狸"` (for zhCN)
3. If term has no zhCN translation, add hint: `Term "Example" in enUS: Example Text`
4. Fuzzy matches (10+ chars) add hints: `Term "SpecialResource" (fuzzy match) in zhCN: 特殊资源`
5. Preprocessed text + hints sent to LLM for translation


### Optimized Multi-threading

Translation processing has been optimized for better performance:

- **Per-language parallelization**: When translating a single mod, all languages are now processed in parallel
- **Faster single-mod translation**: Ideal for quick updates to individual mods
- **Configurable**: Use `--max-threads` to control file-level parallelization if needed

### Licensing

Scripts and build files in the `.github` directory are licensed under the [ANTI-LABOR EXPLOITATION LICENSE 1.1 in combination with GNU General Public License v3.0](/.github/LICENSE). This ensures ethical use and protection of contributors' rights.
