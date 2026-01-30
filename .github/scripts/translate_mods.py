#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: (ALE-1.1 AND GPL-3.0-only)
# Copyright (c) 2022-2025 wuyilingwei
#
# This file is licensed under the ANTI-LABOR EXPLOITATION LICENSE 1.1
# in combination with GNU General Public License v3.0.
# See .github/LICENSE for full license text.
"""
Automated translation script for Timberborn mods
This script processes TOML files and translates missing language entries using LLM
"""

import os
import sys
import toml
import time
import logging
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Set, Tuple

# Add util to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'util'))
from translator import TranslatorLLM


# Global variable to store language names loaded from config
LANGUAGE_NAMES = {}

# Global variable to store glossary
GLOSSARY = {}


def load_language_names_from_config(config: Dict) -> Dict[str, str]:
    """Load language code to full name mapping from configuration"""
    return config.get("languages", {}).get("locale_names", {})


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


def load_glossary(glossary_path: str) -> Dict[str, Dict[str, str]]:
    """
    Load glossary from TOML file
    
    Args:
        glossary_path: Path to _glossary.toml file
        
    Returns:
        Dictionary mapping terms to their translations in different languages
        Format: {"Term": {"zhCN": "翻译", "zhTW": "翻譯", ...}}
    """
    logger = logging.getLogger("load_glossary")
    
    if not os.path.exists(glossary_path):
        logger.warning(f"Glossary file not found: {glossary_path}")
        return {}
    
    try:
        with open(glossary_path, 'r', encoding='utf-8') as f:
            glossary = toml.load(f)
        logger.info(f"Loaded glossary with {len(glossary)} terms")
        return glossary
    except Exception as e:
        logger.error(f"Failed to load glossary: {e}")
        return {}


def merge_glossaries(global_glossary: Dict[str, Dict[str, str]], 
                     local_glossary: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    """
    Merge global and local glossaries, with local taking priority
    
    Args:
        global_glossary: Global glossary dictionary
        local_glossary: Local (mod-specific) glossary dictionary
        
    Returns:
        Merged glossary with local terms overriding global terms
    """
    if not global_glossary:
        return local_glossary or {}
    if not local_glossary:
        return global_glossary
    
    # Start with a copy of global glossary
    merged = dict(global_glossary)
    
    # Override with local glossary terms
    for term, translations in local_glossary.items():
        if term in merged:
            # Merge translations for existing term (local overrides global per language)
            merged[term] = {**merged[term], **translations}
        else:
            # Add new term from local glossary
            merged[term] = translations
    
    return merged


def fuzzy_match_term(text: str, term: str, tolerance: int = 2) -> bool:
    """
    Check if a term fuzzy matches text with a given tolerance (case-insensitive)
    For terms with 10+ characters, allows up to 'tolerance' character differences
    
    Args:
        text: Text to search in
        term: Term to match
        tolerance: Maximum character differences allowed (default: 2)
        
    Returns:
        True if fuzzy match found, False otherwise
    """
    if len(term) < 10:
        # Only exact match for short terms (case-insensitive)
        import re
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        return pattern.search(text) is not None
    
    # For longer terms, check fuzzy match (case-insensitive)
    from difflib import SequenceMatcher
    
    # Check if term appears with minor variations
    text_lower = text.lower()
    term_lower = term.lower()
    
    # Try to find the term or similar substring
    for i in range(len(text) - len(term) + tolerance + 1):
        for length in range(max(len(term) - tolerance, 1), len(term) + tolerance + 1):
            if i + length > len(text):
                continue
            substring = text[i:i+length]
            
            # Calculate similarity
            matcher = SequenceMatcher(None, term_lower, substring.lower())
            ratio = matcher.ratio()
            
            # If very similar (allowing for tolerance characters difference)
            max_diff = tolerance / len(term)
            if ratio >= (1 - max_diff):
                return True
    
    return False


def generate_glossary_hints(
    text: str,
    target_language: str,
    glossary: Dict[str, Dict[str, str]],
    language_priority: List[str],
    default_fuzzy_tolerance: int = 2
) -> Tuple[str, List[str]]:
    """
    Apply glossary replacements and generate hints for missing translations
    
    Args:
        text: Source text to process
        target_language: Target language code
        glossary: Glossary dictionary with English keys and translations
        language_priority: Ordered list of languages (only show first available)
        default_fuzzy_tolerance: Default tolerance for fuzzy matching (default: 2 characters)
        
    Returns:
        Tuple of (preprocessed_text, list of glossary hints)
    """
    if not glossary or not text:
        return text, []
    
    # Sort terms by length (longest first) to avoid partial replacements
    sorted_terms = sorted(glossary.keys(), key=len, reverse=True)
    
    result = text
    hints = []
    processed_terms = set()
    
    for term in sorted_terms:
        term_data = glossary.get(term, {})
        
        # Skip if this is a dictionary with special flags
        skip_hints = False
        fuzzy_tolerance = default_fuzzy_tolerance
        translations = {}
        
        # Check if term_data has special structure with 'translations' key
        if isinstance(term_data, dict):
            if 'skip_hints' in term_data:
                skip_hints = term_data.get('skip_hints', False)
                translations = term_data.get('translations', {})
            elif 'fuzzy_tolerance' in term_data:
                # Has custom fuzzy_tolerance
                fuzzy_tolerance = term_data.get('fuzzy_tolerance', default_fuzzy_tolerance)
                # Remove special keys to get translations
                translations = {k: v for k, v in term_data.items() if k not in ['skip_hints', 'fuzzy_tolerance']}
            else:
                # Regular format: term_data is the translations dict
                translations = term_data
        
        # Check for exact match (case-insensitive)
        import re
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        match = pattern.search(text)
        
        if match:
            if target_language in translations:
                # Exact match with translation available - replace (case-insensitive)
                result = pattern.sub(translations[target_language], result)
                processed_terms.add(term)
            elif not skip_hints and translations:
                # Exact match but no translation for target language - add hint
                # Only show the first available language from priority list
                first_available = None
                for lang in language_priority:
                    if lang in translations:
                        first_available = lang
                        break
                
                if first_available:
                    hint = f'Term "{term}" in {first_available}: {translations[first_available]}'
                    hints.append(hint)
                    processed_terms.add(term)
        
        # Check for fuzzy match (only for longer terms not already processed)
        elif len(term) >= 10 and term not in processed_terms:
            if fuzzy_match_term(text, term, fuzzy_tolerance):
                # Fuzzy match found - add as hint (don't replace)
                if target_language in translations:
                    hint = f'Term "{term}" (fuzzy match) translates to "{translations[target_language]}" in {target_language}'
                    hints.append(hint)
                elif not skip_hints and translations:
                    # Only show the first available language from priority list
                    first_available = None
                    for lang in language_priority:
                        if lang in translations:
                            first_available = lang
                            break
                    
                    if first_available:
                        hint = f'Term "{term}" (fuzzy match) in {first_available}: {translations[first_available]}'
                        hints.append(hint)
                processed_terms.add(term)
    
    return result, hints


def apply_glossary_to_source(
    text: str, 
    target_language: str, 
    glossary: Dict[str, Dict[str, str]],
    language_priority: Optional[List[str]] = None
) -> str:
    """
    Apply glossary replacements to source text before translation
    Replaces English glossary terms with their target language translations
    Terms are replaced from longest to shortest to avoid partial replacements
    
    Args:
        text: Source text to process (in English)
        target_language: Target language code for glossary lookup
        glossary: Glossary dictionary with English keys and language translations
        language_priority: Ordered list of languages for hint priority
        
    Returns:
        Text with English glossary terms replaced with target language translations
    """
    if not glossary or not text:
        return text
    
    # Use the new generate_glossary_hints function but only return preprocessed text
    if language_priority is None:
        language_priority = [target_language]
    
    preprocessed_text, _ = generate_glossary_hints(text, target_language, glossary, language_priority)
    return preprocessed_text


def apply_glossary(text: str, target_language: str, glossary: Dict[str, Dict[str, str]]) -> str:
    """
    Apply glossary replacements to translated text for a specific language
    
    Args:
        text: Text to process (translated text)
        target_language: Target language code
        glossary: Glossary dictionary (can be merged global+local)
        
    Returns:
        Text with glossary terms replaced
    """
    if not glossary or not text:
        return text
    
    # Sort terms by length (longest first) to avoid partial replacements
    sorted_terms = sorted(glossary.keys(), key=len, reverse=True)
    
    result = text
    for term in sorted_terms:
        translations = glossary.get(term, {})
        
        # Handle both old format and new format with special keys
        if isinstance(translations, dict) and 'translations' in translations:
            # New format with skip_hints, fuzzy_tolerance etc.
            actual_translations = translations.get('translations', {})
        else:
            # Old format or regular translations dict
            actual_translations = {k: v for k, v in translations.items() if k not in ['skip_hints', 'fuzzy_tolerance']}
        
        if target_language in actual_translations:
            # Case-insensitive replacement while preserving original case
            import re
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            result = pattern.sub(actual_translations[target_language], result)
    
    return result


def build_translation_prompt(
    key: str,
    new_text: str,
    mod_name: str,
    target_language: str,
    raw: Optional[str] = None,
    current_translation: Optional[str] = None,
    prompt: Optional[str] = None,
    specific_prompt: Optional[str] = None,
    glossary_hints: Optional[List[str]] = None
) -> Tuple[str, str]:
    """
    Build system and user prompts for translation
    
    Args:
        glossary_hints: Optional list of glossary hints to include in prompt
    
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    # System prompt
    lang_name = LANGUAGE_NAMES.get(target_language, target_language)
    system_prompt = (
        f'You are a professional game localization translator specializing in the game "Timberborn" and its mod "{mod_name}". '
        f'Task: Translate the given text into {lang_name}'
        f'Output rules (STRICT) Output ONLY the translated text. Do NOT add explanations, comments, notes, quotes, keep original formatting. Do NOT repeat the source text. Do NOT add prefixes such as "Translation:", "Result:", or similar. If the input is empty, output an empty string.'
    )
    
    # User prompt - build dynamically based on available information
    prompt_parts = [f"Key name: {key}"]
    
    if new_text:
        prompt_parts.append(f'New Text to Translate: "{new_text}"')
    
    if raw:
        prompt_parts.append(f'Original Text (Old): "{raw}"')
    
    if current_translation:
        prompt_parts.append(f'Current Translation: "{current_translation}"')
    
    if prompt:
        prompt_parts.append(f'Field Hint: {prompt}')
    
    if specific_prompt:
        prompt_parts.append(f'Specific Note: {specific_prompt}')
    
    # Add glossary hints if available
    if glossary_hints:
        for hint in glossary_hints:
            prompt_parts.append(f'Glossary Reference: {hint}')
    
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
    prompt: Optional[str] = None,
    glossary: Optional[Dict[str, Dict[str, str]]] = None,
    language_priority: Optional[List[str]] = None
) -> Optional[str]:
    """
    Translate a single entry for a specific language
    
    Args:
        prompt: Optional prompt hint for translation context
        glossary: Optional merged glossary (global + local) to apply before translation
        language_priority: Ordered list of languages for glossary hint priority
    
    Returns:
        Translated text or None if translation not needed/failed
    """
    logger = logging.getLogger("translate_entry")
    
    # Check if this entry should use copy mode (for symbolic fields)
    copy_mode = entry.get("copy", False)
    
    # Determine the text to translate
    has_new_field = "new" in entry
    raw_text = entry.get("raw", "")
    
    # Check if translation exists for this language
    # Empty string is valid translation if raw text is also empty
    has_translation = target_lang in entry and (
        entry.get(target_lang) or 
        (entry.get(target_lang) == "" and raw_text.strip() == "")
    )
    
    # Skip if translation exists and no update needed
    if not has_new_field and has_translation:
        return None
    
    # Handle copy mode: directly copy source text without translation
    if copy_mode:
        source_text = entry.get("new") if has_new_field else entry.get("raw", "")
        logger.debug(f"Copy mode for {key}: copying '{source_text}' to {target_lang}")
        return source_text
    
    # Determine source text: use "new" if available, otherwise use "raw"
    if has_new_field:
        text_to_translate = entry.get("new")
        if text_to_translate is None:
            logger.warning(f"Entry {key} has 'new' field but value is None")
            return None
    else:
        # Missing translation case - use raw text
        text_to_translate = entry.get("raw")
        if text_to_translate is None:
            logger.warning(f"Entry {key} has no 'raw' or 'new' field to translate from")
            return None
        # If raw text is empty, return empty string (valid empty translation)
        if not text_to_translate.strip():
            return ""
    
    # Apply glossary to source text BEFORE translation with hints (if translating a "new" field)
    preprocessed_text = text_to_translate
    glossary_hints = []
    
    if has_new_field and glossary:
        if language_priority is None:
            language_priority = [target_lang]
        
        preprocessed_text, glossary_hints = generate_glossary_hints(
            text_to_translate, 
            target_lang, 
            glossary,
            language_priority
        )
        
        if preprocessed_text != text_to_translate:
            logger.debug(f"Glossary preprocessing for {target_lang}: '{text_to_translate}' -> '{preprocessed_text}'")
        
        if glossary_hints:
            logger.debug(f"Generated {len(glossary_hints)} glossary hints for {key}")
    
    # Get context information
    raw = entry.get("raw")
    current_translation = entry.get(target_lang)
    specific_prompt = entry.get("prompt")
    
    # Build prompts with glossary hints
    system_prompt, user_prompt = build_translation_prompt(
        key=key,
        new_text=preprocessed_text,  # Use preprocessed text with glossary applied
        mod_name=mod_name,
        target_language=target_lang,
        raw=raw if has_new_field and raw != text_to_translate else None,  # Only show old text if different from new
        current_translation=current_translation,
        prompt=prompt,
        specific_prompt=specific_prompt,
        glossary_hints=glossary_hints if glossary_hints else None
    )
    
    # Translate with preprocessed text
    logger.info(f"Translating {key} to {target_lang}")
    translation = translator.translate(
        text=preprocessed_text,  # Send preprocessed text to LLM
        target_language=target_lang,
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )
    
    # Validate translation result
    # Empty translation is only valid if the original raw text is also empty
    if translation is not None:
        if not translation and raw and raw.strip():
            # Translation is empty but original text is not - invalid result
            logger.warning(f"Translation returned empty for non-empty original text in {key}")
            return None
        
        # Strip extra quotes if present and not in original
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
    
    # Extract mod metadata from _meta section (always required now)
    meta_section = data.get("_meta", {})
    mod_name = meta_section.get("name", filename.replace('.toml', ''))
    prompt = meta_section.get("prompt")
    
    # Extract mod-local glossary from _meta section
    local_glossary = meta_section.get("glossary", {})
    
    # Merge global and local glossaries (local takes priority)
    merged_glossary = merge_glossaries(GLOSSARY, local_glossary)
    if local_glossary:
        logger.info(f"Using {len(local_glossary)} local glossary terms for {filename}")
    
    translations_made = 0
    entries_processed = 0
    modified = False
    
    # Process each entry
    for key, entry in data.items():
        # Skip metadata sections
        if key in ["name", "prompt", "_meta"]:  # Changed field_prompt to prompt
            continue
        
        if not isinstance(entry, dict):
            continue
        
        # Check if this entry needs translation
        # 1. Has "new" field - needs retranslation
        # 2. Missing translations for some languages (but not if raw text is empty)
        has_new_field = "new" in entry
        raw_text = entry.get("raw", "")
        
        # Only consider a language missing if:
        # - The language field doesn't exist or is empty/None
        # - AND the raw text is not empty (empty raw text = valid empty translation)
        missing_languages = [
            lang for lang in target_languages 
            if (lang not in entry or not entry.get(lang)) and raw_text and raw_text.strip()
        ]
        
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
        
        # Translate for each target language in parallel
        all_translations_successful = True
        new_translations = {}
        
        # Use ThreadPoolExecutor to parallelize translation by language
        with ThreadPoolExecutor(max_workers=min(len(languages_to_translate), 10)) as executor:
            # Submit translation tasks for all languages
            future_to_lang = {
                executor.submit(
                    translate_entry,
                    translator=translator,
                    key=key,
                    entry=entry,
                    target_lang=lang,
                    mod_name=mod_name,
                    prompt=prompt,  # Changed from field_prompt to prompt
                    glossary=merged_glossary,
                    language_priority=target_languages
                ): lang
                for lang in languages_to_translate
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_lang):
                lang = future_to_lang[future]
                try:
                    translation = future.result()
                    # Accept translation if it's not None (empty string is valid if raw is also empty)
                    if translation is not None:
                        new_translations[lang] = translation
                        translations_made += 1
                    else:
                        logger.warning(f"Failed to translate {key} to {lang}")
                        all_translations_successful = False
                except Exception as e:
                    logger.error(f"Error translating {key} to {lang}: {e}")
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
    dry_run: bool = False,
    max_time: Optional[int] = None
) -> None:
    """
    Process all TOML files in the data directory
    
    Note: With the optimized multi-threading structure, translations within each mod
    are parallelized by language. The max_threads parameter controls whether files
    themselves are also processed in parallel (max_threads > 1) or sequentially 
    (max_threads = 1). For best single-mod performance, use max_threads = 1 which
    allows maximum parallelization of languages within the mod.
    
    Args:
        data_dir: Directory containing TOML files
        translator: Translator instance
        target_languages: List of target language codes
        max_threads: Maximum number of concurrent file processing threads
        dry_run: If True, don't write changes
        max_time: Maximum processing time in seconds. If set, stops taking new entries when time is up.
    """
    logger = logging.getLogger("process_all_files")
    
    start_time = time.time()
    
    # Find all TOML files, excluding _glossary.toml
    all_toml_files = list(Path(data_dir).glob("*.toml"))
    toml_files = [f for f in all_toml_files if not f.name.startswith('_')]
    logger.info(f"Found {len(toml_files)} TOML files to process (excluded {len(all_toml_files) - len(toml_files)} system files)")
    
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
                # Check timeout before processing result
                if max_time and (time.time() - start_time) >= max_time:
                    logger.warning(f"Time limit of {max_time} seconds reached. Stopping processing of new files.")
                    # Cancel remaining futures
                    for f in futures:
                        if not f.done():
                            f.cancel()
                    break
                
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
            # Check timeout before processing each file
            if max_time and (time.time() - start_time) >= max_time:
                logger.warning(f"Time limit of {max_time} seconds reached. Stopping processing of remaining files.")
                logger.info(f"Processed {len(toml_files) - toml_files.index(toml_file)} of {len(toml_files)} files before timeout")
                break
            
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
        default=".github/config/config.toml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directory containing TOML files"
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
    parser.add_argument(
        "--max-time",
        type=int,
        help="Maximum processing time in seconds. Script will stop taking new entries when time is up."
    )
    parser.add_argument(
        "--glossary",
        default="data/_glossary.toml",
        help="Path to glossary file (default: data/_glossary.toml)"
    )
    
    args = parser.parse_args()
    
    try:
        # Load configuration first
        config = load_config(args.config)
        
        # Load language names from config
        global LANGUAGE_NAMES
        LANGUAGE_NAMES = load_language_names_from_config(config)
        
        # Load glossary
        global GLOSSARY
        glossary_path = args.glossary
        GLOSSARY = load_glossary(glossary_path)
        
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
        
        # Load target languages from config
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
        
        if args.max_time:
            logger.info(f"Maximum processing time: {args.max_time} seconds")
        
        # Process all files
        process_all_files(
            data_dir=args.data_dir,
            translator=translator,
            target_languages=target_languages,
            max_threads=max_threads,
            dry_run=args.dry_run,
            max_time=args.max_time
        )
        
        logger.info("All done!")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
