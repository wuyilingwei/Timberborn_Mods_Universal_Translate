#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: (ALE-1.1 AND GPL-3.0-only)
# Copyright (c) 2022-2025 wuyilingwei
#
# This file is licensed under the ANTI-LABOR EXPLOITATION LICENSE 1.1
# in combination with GNU General Public License v3.0.
# See .github/LICENSE for full license text.
"""
Sync ingame TOML files from raw CSV source files.

Reads .github/data/raw/*.txt (CSV format: ID, Text, Comment) and
generates/updates the corresponding data/_ingame*.toml files.

Change detection:
  - New entry in raw → add entry with raw = Text
  - Entry text changed vs TOML raw field → set new = Text (triggers retranslation)
  - Entry unchanged → no change

These ingame TOML files are translated only for languages in
config.languages.supported that are NOT in config.languages.game_supported.
"""

import argparse
import csv
import io
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import toml


def _normalize_whitespace(text: str) -> str:
    """Replace non-breaking spaces (U+00A0) with regular spaces.

    The Python ``toml`` library cannot round-trip \\xa0 correctly: it
    serialises the character as literal ``xa0`` text, which then reads
    back as a different string.  Normalising to ASCII space before
    storage prevents an infinite sync→translate loop.

    This also repairs the *corrupted* form (literal 3-char ``xa0``)
    that earlier buggy serialisations left in existing TOML files.
    """
    if not text:
        return text
    # Fix actual non-breaking space character (U+00A0)
    text = text.replace("\xa0", " ")
    # Fix corrupted literal "xa0" left by the toml library bug.
    # The toml lib writes \xa0 as the three ASCII chars 'x','a','0'.
    # This sequence never appears in legitimate game localisation text.
    text = text.replace("xa0", " ")
    return text


# Mapping: raw filename → (toml filename, meta name)
RAW_TO_INGAME: Dict[str, Tuple[str, str]] = {
    "enUS.txt":              ("_ingame.toml",       "Timberborn Ingame"),
    "enUS_donottranslate.txt": ("_ingame_des.toml", "Timberborn Ingame Description"),
}


def setup_logging(log_level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def load_config(config_path: str) -> Dict:
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return toml.load(f)


def parse_raw_csv(raw_path: str) -> List[Tuple[str, str, str]]:
    """
    Parse a raw CSV file (ID, Text, Comment) and return list of (id, text, comment).
    Handles multi-line text fields correctly (Python csv module handles quoted fields).
    """
    entries: List[Tuple[str, str, str]] = []
    with open(raw_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry_id = (row.get("ID") or "").strip()
            text = row.get("Text") or ""
            comment = row.get("Comment") or ""
            if entry_id:
                entries.append((entry_id, text, comment))
    return entries


def load_ingame_toml(toml_path: str, meta_name: str) -> Dict:
    """Load an existing ingame TOML or create a fresh skeleton."""
    if os.path.exists(toml_path):
        with open(toml_path, "r", encoding="utf-8") as f:
            data = toml.load(f)
        # Ensure the ingame marker is present
        if "_meta" not in data:
            data["_meta"] = {}
        data["_meta"]["ingame"] = True
        data["_meta"]["name"] = meta_name
        return data
    return {
        "_meta": {
            "name": meta_name,
            "ingame": True,
        }
    }


def write_ingame_toml(toml_path: str, data: Dict) -> None:
    """Write the ingame TOML back to disk, preserving unix line endings."""
    toml_text = toml.dumps(data)
    with open(toml_path, "w", encoding="utf-8", newline="") as f:
        f.write(toml_text)


def sync_one_file(
    raw_path: str,
    toml_path: str,
    meta_name: str,
    logger: logging.Logger,
) -> Tuple[int, int, int]:
    """
    Sync a single raw CSV → ingame TOML file.

    Returns:
        (added, updated, unchanged) entry counts.
    """
    raw_entries = parse_raw_csv(raw_path)
    logger.info(f"Parsed {len(raw_entries)} entries from {os.path.basename(raw_path)}")

    data = load_ingame_toml(toml_path, meta_name)

    added = updated = unchanged = 0

    for entry_id, text, comment in raw_entries:
        # Normalise non-breaking spaces so the toml library round-trip
        # bug (\xa0 → literal "xa0") never triggers a false mismatch.
        text = _normalize_whitespace(text)

        if entry_id not in data:
            # Brand-new entry — add with raw = text so translate step picks it up
            entry: Dict = {
                "raw": text,
                "status": "normal",
            }
            if comment:
                entry["prompt"] = comment
            data[entry_id] = entry
            added += 1
            logger.debug(f"  + added: {entry_id}")
        else:
            existing = data[entry_id]
            existing_raw = _normalize_whitespace(existing.get("raw", ""))

            # Fix pre-existing corrupted raw values (literal "xa0" from
            # earlier toml.dumps bug).  Overwrite with normalised text so
            # the comparison below sees them as equal.
            if existing_raw != existing.get("raw", ""):
                existing["raw"] = existing_raw

            # Keep prompt in sync with upstream comment
            if comment:
                existing["prompt"] = comment
            elif "prompt" in existing and not comment:
                # Upstream comment removed — drop local prompt too
                del existing["prompt"]

            if existing_raw != text:
                # Text changed upstream — set `new` to trigger retranslation
                existing["new"] = text
                updated += 1
                logger.info(f"  ~ updated (new field set): {entry_id}")
            else:
                unchanged += 1

    write_ingame_toml(toml_path, data)
    logger.info(
        f"Synced {os.path.basename(toml_path)}: "
        f"{added} added, {updated} updated, {unchanged} unchanged"
    )
    return added, updated, unchanged


def sync_all(
    raw_dir: str,
    data_dir: str,
    logger: logging.Logger,
) -> None:
    """Run sync for all three ingame file pairs."""
    total_added = total_updated = total_unchanged = 0

    for raw_filename, (toml_filename, meta_name) in RAW_TO_INGAME.items():
        raw_path = os.path.join(raw_dir, raw_filename)
        toml_path = os.path.join(data_dir, toml_filename)

        if not os.path.exists(raw_path):
            logger.warning(f"Raw file not found, skipping: {raw_path}")
            continue

        logger.info(f"--- Syncing {raw_filename} → {toml_filename} ---")
        added, updated, unchanged = sync_one_file(raw_path, toml_path, meta_name, logger)
        total_added += added
        total_updated += updated
        total_unchanged += unchanged

    logger.info(
        f"Sync complete. Total: {total_added} added, "
        f"{total_updated} updated, {total_unchanged} unchanged"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync ingame TOML files from raw CSV source files"
    )
    parser.add_argument(
        "--config",
        default=".github/config/config.toml",
        help="Path to configuration file",
    )
    parser.add_argument(
        "--raw-dir",
        default=".github/data/raw",
        help="Directory containing raw CSV source files",
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directory containing ingame TOML files",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )
    args = parser.parse_args()

    setup_logging("DEBUG" if args.verbose else "INFO")
    logger = logging.getLogger("sync_ingame")

    sync_all(
        raw_dir=args.raw_dir,
        data_dir=args.data_dir,
        logger=logger,
    )


if __name__ == "__main__":
    main()
