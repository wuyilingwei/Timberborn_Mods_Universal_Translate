#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import toml
import csv
import shutil
import sys
from pathlib import Path


def load_config(config_path=".github/config/config.toml"):
    """Load configuration from TOML file"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return toml.load(f)
    except FileNotFoundError:
        print(f"[ERROR] Configuration file not found: {config_path}")
        return {}
    except Exception as e:
        print(f"[ERROR] Failed to load configuration: {e}")
        return {}


def load_protected_fields_from_csv(csv_path):
    """Load protected field IDs from CSV file"""
    protected_fields = set()
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'ID' in row and row['ID'].strip():
                    protected_fields.add(row['ID'].strip())
        print(f"[Info] Loaded {len(protected_fields)} protected fields from {csv_path}")
    except FileNotFoundError:
        print(f"[WARNING] Protected strings file not found: {csv_path}")
    except Exception as e:
        print(f"[ERROR] Failed to load protected fields from {csv_path}: {e}")
    return protected_fields


def get_protected_fields(config):
    """Get all protected fields from config and CSV file"""
    protected_fields = set()
    
    # Get build config
    build_config = config.get("build", {})
    
    # Get extra protected string IDs from config
    extra_protect_ids = build_config.get("extra_protect_string_ids", [])
    protected_fields.update(extra_protect_ids)
    
    # Load protected fields from CSV file
    protect_file = build_config.get("protect_string_ids_file")
    if protect_file:
        csv_path = f".github/config/{protect_file}"
        csv_protected_fields = load_protected_fields_from_csv(csv_path)
        protected_fields.update(csv_protected_fields)
    
    print(f"[Info] Total protected fields: {len(protected_fields)}")
    return protected_fields


def get_supported_languages(config):
    """Get supported languages from config"""
    languages = config.get("languages", {}).get("supported", [])
    if not languages:
        print("[WARNING] No supported languages found in config, using fallback list")
        languages = ["enUS", "zhCN", "zhTW", "ruRU", "jaJP", "frFR", "deDE", "plPL", "ptBR", "koKR"]
    
    print(f"[Info] Using languages: {', '.join(languages)}")
    return set(languages)


def convert_toml_to_csv(data_dir, mod_dir, config_path=".github/config/config.toml"):
    """将TOML文件转换为CSV文件"""
    
    # Load configuration
    config = load_config(config_path)
    if not config:
        print("[ERROR] Failed to load configuration, exiting")
        return
    
    protected_fields = get_protected_fields(config)
    supported_languages = get_supported_languages(config)

    for file_name in os.listdir(data_dir):
        if file_name.endswith(".toml"):
            # 提取 mod_id（不再区分版本）
            match = re.search(r"(\d+)\.toml", file_name)
            if not match:
                print(f"Skipping file {file_name}: does not match expected pattern")
                continue
            mod_id = match.group(1)
            
            toml_path = os.path.join(data_dir, file_name)
            output_dir = os.path.join(mod_dir, "Localizations")
            os.makedirs(output_dir, exist_ok=True)

            # 读取 TOML 文件
            try:
                with open(toml_path, "r", encoding="utf-8") as toml_file:
                    data = toml.load(toml_file)
                
                # 使用配置中的支持语言列表，并检查TOML中哪些语言有翻译
                available_languages = set()
                for key, translations in data.items():
                    if isinstance(translations, dict):
                        for lang_code in translations.keys():
                            if lang_code in supported_languages:
                                available_languages.add(lang_code)
                
                # 只为有翻译内容的语言生成CSV文件
                all_languages = available_languages
                
                if not all_languages:
                    print(f"[Info] No supported language translations found in {file_name}")
                    continue
                
                # 为每种语言生成 CSV 文件
                generated_files = []
                for lang_code in all_languages:
                    csv_file_name = f"{lang_code}_{mod_id}.csv"
                    csv_path = os.path.join(output_dir, csv_file_name)
                    
                    empty_entries_count = 0
                    
                    with open(csv_path, "w", encoding="utf-8", newline="") as csv_file:
                        writer = csv.writer(csv_file)
                        writer.writerow(["ID", "Text", "Comment"])
                        
                        # 遍历所有翻译条目
                        for translation_key, translations in data.items():
                            if isinstance(translations, dict) and lang_code in translations:
                                translation_text = translations[lang_code]
                                # 检查空字符串并输出警告
                                if not translation_text or not translation_text.strip():
                                    empty_entries_count += 1
                                    print(f"[Warning] Empty translation for key '{translation_key}' in language '{lang_code}' (file: {file_name})")
                                else:
                                    # 如果文本以空格开头，为其添加双引号以防止游戏忽略前导空格
                                    processed_text = translation_text
                                    if translation_text.startswith(' '):
                                        processed_text = f'"{translation_text}"'
                                        print(f"[Info] Added quotes to preserve leading space for key '{translation_key}' in language '{lang_code}' (file: {file_name})")
                                    
                                    writer.writerow([translation_key, processed_text, "-"])
                    
                    if empty_entries_count > 0:
                        print(f"[Info] Skipped {empty_entries_count} empty entries for {lang_code} in {file_name}")
                    
                    generated_files.append((csv_file_name, csv_path))
                        
            except Exception as e:
                print(f"[ERROR] Failed to process {toml_path}: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: convert_toml_to_csv.py <data_dir> <mod_dir> [config_path]")
        sys.exit(1)
    
    data_dir = sys.argv[1]
    mod_dir = sys.argv[2]
    config_path = sys.argv[3] if len(sys.argv) > 3 else ".github/config/config.toml"
    
    convert_toml_to_csv(data_dir, mod_dir, config_path)
