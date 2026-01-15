#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automated translation script for Timberborn mods
This script processes TOML files and translates missing language entries using LLM
"""

import os
import sys
import toml
import logging
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Set, Tuple

# Add util to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'util'))
from translator import TranslatorLLM


# Language code to full name mapping
LANGUAGE_NAMES = {
    "enUS": "English (US)",
    "zhCN": "Simplified Chinese",
    "zhTW": "Traditional Chinese",
    "ruRU": "Russian",
    "jaJP": "Japanese",
    "frFR": "French",
    "deDE": "German",
    "plPL": "Polish",
    "ptBR": "Brazilian Portuguese",
    "koKR": "Korean"
}


def setup_logging(log_level: str = "INFO") -> None:
    """Setup logging configuration"""
    # Convert string to logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def load_config(config_path: str) -> Dict:
    """Load configuration from TOML file"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = toml.load(f)
    
    return config


def load_target_languages(config: Dict) -> List[str]:
    """Load target languages from configuration"""
    languages = config.get("languages", {}).get("supported", [])
    
    if not languages:
        raise ValueError("No languages defined in configuration")
    
    logging.info(f"Target languages: {', '.join(languages)}")
    return languages


def build_translation_prompt(
    key: str,
    new_text: str,
    mod_name: str,
    target_language: str,
    raw: Optional[str] = None,
    current_translation: Optional[str] = None,
    field_prompt: Optional[str] = None,
    specific_prompt: Optional[str] = None
) -> Tuple[str, str]:
    """
    Build system and user prompts for translation
    
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    # System prompt
    lang_name = LANGUAGE_NAMES.get(target_language, target_language)
    system_prompt = (
        f'You are a professional game translator specializing in "Timberborn" mod {mod_name}. '
        f'Translate the given text to {lang_name} and only return the translated text.'
    )
    
    # User prompt - build dynamically based on available information
    prompt_parts = [f"Key name: {key}"]
    
    if new_text:
        prompt_parts.append(f'New Text to Translate: "{new_text}"')
    
    if raw:
        prompt_parts.append(f'Original Text (Old): "{raw}"')
    
    if current_translation:
        prompt_parts.append(f'Current Translation: "{current_translation}"')
    
    if field_prompt:
        prompt_parts.append(f'Field Hint: {field_prompt}')
    
    if specific_prompt:
        prompt_parts.append(f'Specific Note: {specific_prompt}')
    
    user_prompt = " - ".join(prompt_parts)
    
    return system_prompt, user_prompt


def strip_extra_quotes(text: str, reference_text: str) -> str:
    """
    Strip extra quotes from translated text if the reference doesn't have them.
    
    This handles cases where LLM adds extra quotes like:
    - raw: "Mostly helpful billboards" -> zhTW: '"大多數有幫助的廣告牌"'
    
    Args:
        text: Translated text that might have extra quotes
        reference_text: Reference text (usually raw field) to check quote pattern
        
    Returns:
        Text with extra quotes removed if appropriate
    """
    if not text or not reference_text:
        return text
    
    # Check if reference text starts and ends with quotes
    ref_has_quotes = reference_text.startswith('"') and reference_text.endswith('"')
    
    # If translation has quotes but reference doesn't, remove them
    if not ref_has_quotes and text.startswith('"') and text.endswith('"') and len(text) > 2:
        # Remove leading and trailing quotes
        text = text[1:-1]
    
    return text


def translate_entry(
    translator: TranslatorLLM,
    key: str,
    entry: Dict,
    target_lang: str,
    mod_name: str,
    field_prompt: Optional[str] = None
) -> Optional[str]:
    """
    Translate a single entry for a specific language
    
    Returns:
        Translated text or None if translation not needed/failed
    """
    logger = logging.getLogger("translate_entry")
    
    # Determine the text to translate
    has_new_field = "new" in entry
    has_translation = target_lang in entry and entry.get(target_lang)
    
    # Skip if translation exists and no update needed
    if not has_new_field and has_translation:
        return None
    
    # Determine source text: use "new" if available, otherwise use "raw"
    if has_new_field:
        text_to_translate = entry.get("new")
        if text_to_translate is None:
            logger.warning(f"Entry {key} has 'new' field but value is None")
            return None
    else:
        # Missing translation case - use raw text
        text_to_translate = entry.get("raw")
        if not text_to_translate:
            logger.warning(f"Entry {key} has no 'raw' or 'new' field to translate from")
            return None
    
    # Get context information
    raw = entry.get("raw")
    current_translation = entry.get(target_lang)
    specific_prompt = entry.get("prompt")
    
    # Build prompts
    system_prompt, user_prompt = build_translation_prompt(
        key=key,
        new_text=text_to_translate,
        mod_name=mod_name,
        target_language=target_lang,
        raw=raw if has_new_field and raw != text_to_translate else None,  # Only show old text if different from new
        current_translation=current_translation,
        field_prompt=field_prompt,
        specific_prompt=specific_prompt
    )
    
    # Translate
    logger.info(f"Translating {key} to {target_lang}")
    translation = translator.translate(
        text=text_to_translate,
        target_language=target_lang,
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )
    
    # Strip extra quotes if present and not in original
    if translation:
        reference_text = raw if raw else text_to_translate
        translation = strip_extra_quotes(translation, reference_text)
    
    return translation


def process_toml_file(
    toml_path: str,
    translator: TranslatorLLM,
    target_languages: List[str],
    dry_run: bool = False
) -> Tuple[int, int]:
    """
    Process a single TOML file and translate missing entries
    
    Returns:
        Tuple of (translations_made, entries_processed)
    """
    logger = logging.getLogger("process_toml_file")
    filename = os.path.basename(toml_path)
    logger.info(f"Processing {filename}")
    
    # Load TOML file
    try:
        with open(toml_path, 'r', encoding='utf-8') as f:
            data = toml.load(f)
    except Exception as e:
        logger.error(f"Failed to load {filename}: {e}")
        return 0, 0
    
    # Extract mod metadata
    mod_name = data.get("name", filename.replace('.toml', ''))
    field_prompt = data.get("field_prompt")
    
    translations_made = 0
    entries_processed = 0
    modified = False
    
    # Process each entry
    for key, entry in data.items():
        if not isinstance(entry, dict):
            continue
        
        # Check if this entry needs translation
        # 1. Has "new" field - needs retranslation
        # 2. Missing translations for some languages
        has_new_field = "new" in entry
        missing_languages = [lang for lang in target_languages if lang not in entry or not entry.get(lang)]
        
        if not has_new_field and not missing_languages:
            # Nothing to translate
            continue
        
        entries_processed += 1
        
        if has_new_field:
            logger.info(f"Processing entry with 'new' field: {key}")
            # Translate for all languages when "new" field exists
            languages_to_translate = target_languages
        else:
            logger.info(f"Processing entry with missing translations: {key} (missing: {', '.join(missing_languages)})")
            # Only translate missing languages
            languages_to_translate = missing_languages
        
        # Translate for each target language
        all_translations_successful = True
        new_translations = {}
        
        for lang in languages_to_translate:
            translation = translate_entry(
                translator=translator,
                key=key,
                entry=entry,
                target_lang=lang,
                mod_name=mod_name,
                field_prompt=field_prompt
            )
            
            if translation:
                new_translations[lang] = translation
                translations_made += 1
            else:
                logger.warning(f"Failed to translate {key} to {lang}")
                all_translations_successful = False
        
        # Update entry if translations were successful
        if new_translations and not dry_run:
            # If has "new" field, update raw field with new text
            if has_new_field:
                entry["raw"] = entry["new"]
            
            # Update translations
            for lang, translation in new_translations.items():
                entry[lang] = translation
            
            # Remove "new" field after successful translation (only if all languages translated)
            if has_new_field and all_translations_successful:
                del entry["new"]
                logger.info(f"Completed translation for {key}, removed 'new' field")
            
            modified = True
    
    # Save modified TOML file
    if modified and not dry_run:
        try:
            with open(toml_path, 'w', encoding='utf-8') as f:
                toml.dump(data, f)
            logger.info(f"Saved updates to {filename}")
        except Exception as e:
            logger.error(f"Failed to save {filename}: {e}")
    
    return translations_made, entries_processed


def process_all_files(
    data_dir: str,
    translator: TranslatorLLM,
    target_languages: List[str],
    max_threads: int = 1,
    dry_run: bool = False
) -> None:
    """Process all TOML files in the data directory"""
    logger = logging.getLogger("process_all_files")
    
    # Find all TOML files
    toml_files = list(Path(data_dir).glob("*.toml"))
    logger.info(f"Found {len(toml_files)} TOML files to process")
    
    if not toml_files:
        logger.warning("No TOML files found")
        return
    
    total_translations = 0
    total_entries = 0
    
    if max_threads > 1:
        # Process files in parallel
        logger.info(f"Processing files with {max_threads} threads")
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = {
                executor.submit(
                    process_toml_file,
                    str(toml_file),
                    translator,
                    target_languages,
                    dry_run
                ): toml_file
                for toml_file in toml_files
            }
            
            for future in as_completed(futures):
                toml_file = futures[future]
                try:
                    translations, entries = future.result()
                    total_translations += translations
                    total_entries += entries
                except Exception as e:
                    logger.error(f"Error processing {toml_file}: {e}")
    else:
        # Process files sequentially
        logger.info("Processing files sequentially")
        for toml_file in toml_files:
            try:
                translations, entries = process_toml_file(
                    str(toml_file),
                    translator,
                    target_languages,
                    dry_run
                )
                total_translations += translations
                total_entries += entries
            except Exception as e:
                logger.error(f"Error processing {toml_file}: {e}")
    
    logger.info(f"Translation complete!")
    logger.info(f"Processed {total_entries} entries")
    logger.info(f"Made {total_translations} translations")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Automated translation for Timberborn mods"
    )
    parser.add_argument(
        "--config",
        default=".github/config/translate.toml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directory containing TOML files"
    )
    parser.add_argument(
        "--lang-file",
        default="info/languages.txt",
        help="File containing target languages (deprecated, use config file instead)"
    )
    parser.add_argument(
        "--api-token",
        help="API token for LLM (overrides secrets.LLM_TOKEN)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without making changes"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging (overrides config log level)"
    )
    parser.add_argument(
        "--log-file",
        help="Path to log file (default: no file output, only console)"
    )
    
    args = parser.parse_args()
    
    try:
        # Load configuration first
        config = load_config(args.config)
        
        # Setup logging with config-based or command-line level
        log_config = config.get("logging", {})
        if args.verbose:
            log_level = "DEBUG"
        else:
            log_level = log_config.get("level", "INFO")
        
        setup_logging(log_level)
        logger = logging.getLogger("main")
        
        # Add file handler if log file specified
        if args.log_file:
            file_handler = logging.FileHandler(args.log_file, mode='w', encoding='utf-8')
            file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
            )
            logging.getLogger().addHandler(file_handler)
            logger.info(f"Logging to file: {args.log_file}")
        
        logger.info("Loading configuration...")
        
        # Get API token
        api_token = args.api_token
        if not api_token:
            # Try environment variable first
            api_token = os.environ.get('LLM_TOKEN') or os.environ.get('OPENAI_API_KEY')
        
        if not api_token:
            # Try to get from secrets module (if it exists and has LLM_TOKEN attribute)
            try:
                import secrets as secrets_module
                if hasattr(secrets_module, 'LLM_TOKEN'):
                    api_token = secrets_module.LLM_TOKEN
            except (ImportError, AttributeError):
                pass
        
        if not api_token:
            logger.error("API token not found. Please provide via --api-token, secrets.LLM_TOKEN, or LLM_TOKEN/OPENAI_API_KEY environment variable")
            sys.exit(1)
        
        # Load target languages from config (with fallback to lang_file for backward compatibility)
        logger.info("Loading target languages...")
        target_languages = load_target_languages(config)
        
        # Initialize translator
        logger.info("Initializing translator...")
        llm_config = config.get("llm", {})
        rate_config = config.get("rate_limiter", {})
        
        rpm = rate_config.get("max_requests_per_minute", 10)
        rate_limit = f"{rpm}/m"
        
        translator = TranslatorLLM(
            api_token=api_token,
            model=llm_config.get("model", "gpt-4o-mini"),
            api_url=llm_config.get("api_url", "https://api.openai.com/v1/chat/completions"),
            min_length=llm_config.get("min_length", 1),
            max_length=llm_config.get("max_length", 5000),
            rate_limit=rate_limit
        )
        
        max_threads = rate_config.get("max_threads", 1)
        
        if args.dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
        
        # Process all files
        process_all_files(
            data_dir=args.data_dir,
            translator=translator,
            target_languages=target_languages,
            max_threads=max_threads,
            dry_run=args.dry_run
        )
        
        logger.info("All done!")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
