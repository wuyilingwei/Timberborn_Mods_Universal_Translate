# Contributing to Timberborn Mods Universal Translate

## Join us

First you need a GitHub account, if not, [sign up](https://github.com/signup) one. Then fill this form [JOIN US](https://github.com/wuyilingwei/Timberborn_Mods_Universal_Translate/issues/new?template=11-JOIN_US.yml), then I will give you edit permissions for the repository.

You can use any git software (such as [Github desktop](https://github.com/apps/desktop)) + text editor (such as [VSC](https://code.visualstudio.com/download)) to edit and upload your changes. Or, just edit in online editor. We do not require signatures for commits.

An automatic script will create the latest language CSV files based on `/data`, publish every day.

## Contributing to Translations

### Mod Translations
Edit the appropriate TOML files in the `/data` directory. See [DATA_STRUCTURE.md](DATA_STRUCTURE.md) for detailed format documentation.

### Global Glossary
The global glossary (`data/_glossary.toml`) provides translations for common game terms used across multiple mods:

- **Add new terms**: Common words that appear in many mods (e.g., "tank", "pump", "building")
- **Use lowercase**: Terms are case-insensitive, so define only lowercase versions
- **Proper names**: Add `skip_hints = true` for game-specific names (e.g., "Timberborn", "Folktails")
- **Consistency**: Ensure translations match existing style and terminology

Example:
```toml
["water"]
zhCN = "水"
zhTW = "水"

["Timberborn"]  
skip_hints = true
zhCN = "海狸浮生记"
zhTW = "海狸浮生記"
```

## Our rules

It uses both of AI and manual work, with AI responsible for providing translation support as quickly as possible and reducing workload, and manual work for proofreading and modification.

We are not responsible for the accuracy of the translated text.

The content that is not accepted for translation is:

 - Built in ID: These keys be used internally in the game. Modifying it may cause unpredictable modifications to the raw game and violate our "universal" principle. Players who do not install the corresponding mod may be modified. Of course, you don't need to worry about this; the build script will automatically check all key-value pairs and remove any known built-in key-value pairs.
 - Any content that violates public order and morals will not be translated to avoid potential problems. This includes but is not limited to: racial discrimination, adult content, etc.
