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

First you need a GitHub account, then fill in [JOIN US](https://github.com/wuyilingwei/Timberborn_Mods_Universal_Translate/issues), and then I will give you editing permissions for the repository.

You can use any git software (such as [Github desktop](https://github.com/apps/desktop)) + text editor (such as [VSC](https://code.visualstudio.com/download)) to edit and upload your changes. We do not require signatures for commits.

An automatic script will create the latest language CSV files based on `/data`, publish every day.

## Our rules

It uses both of AI and manual work, with AI responsible for providing translation support as quickly as possible and reducing workload, and manual work for proofreading and modification.

We are not responsible for the accuracy of the translated text.

The content that is not accepted for translation is:

 - Built in ID: These keys be used internally in the game. Modifying it may cause unpredictable modifications to the raw game and violate our "universal" principle. Players who do not install the corresponding mod may be modified.
 - Any content that violates public order and morals will not be translated to avoid potential problems. This includes but is not limited to: racial discrimination, adult content, etc.

## Translation Features

### Glossary Support

The translation system supports both global and mod-local glossaries for consistent translation of key terms.

**Global Glossary (`glossary.toml`):**
- Provides direct mappings for common game-specific vocabulary like "Timberborn", "Beaver", "District", etc.
- Applied to all mods during translation
- Terms are replaced after LLM translation when processing "new" fields

**Mod-Local Glossary:**
- Individual mods can define their own glossary terms in a `[mod_local]` section
- Local glossary terms override global glossary (when there's a conflict)
- Supports partial language definitions (you don't need to define all languages)

**Example mod TOML structure with local glossary:**
```toml
name = "My Mod"
field_prompt = "Optional extra hints"

# Metadata section for mod-specific configuration
[_meta]
# Optional: Override mod name if needed
# name = "Different Display Name"

# Optional: Additional prompts (not used by translation script)
# prompt = "Extra translation hints"

# Mod-local glossary - overrides global glossary terms
[_meta.glossary."CustomTerm"]
zhCN = "自定义术语"
zhTW = "自訂術語"
# Only define the languages you need

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

### Optimized Multi-threading

Translation processing has been optimized for better performance:

- **Per-language parallelization**: When translating a single mod, all languages are now processed in parallel
- **Faster single-mod translation**: Ideal for quick updates to individual mods
- **Configurable**: Use `--max-threads` to control file-level parallelization if needed

### Licensing

Scripts and build files in the `.github` directory are licensed under the [ANTI-LABOR EXPLOITATION LICENSE 1.1 in combination with GNU General Public License v3.0](/.github/LICENSE). This ensures ethical use and protection of contributors' rights.
