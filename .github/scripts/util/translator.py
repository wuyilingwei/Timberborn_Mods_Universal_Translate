# SPDX-License-Identifier: (ALE-1.1 AND GPL-3.0-only)
# Copyright (c) 2022-2025 wuyilingwei
#
# This file is licensed under the ANTI-LABOR EXPLOITATION LICENSE 1.1
# in combination with GNU General Public License v3.0.
# See .github/LICENSE for full license text.
"""
Translator module for Timberborn mods translation
Adapted from https://github.com/wuyilingwei/Timberborn_Tools
"""
import time
import json
import logging
import threading
import requests
from typing import Optional


class TranslatorLLM:
    """
    OPENAI-STYLED LLM API Translator with rate limiting and cost tracking
    """
    
    # OpenAI pricing per 1K tokens (as of 2024, update as needed)
    MODEL_PRICES = {
        "gpt-5-nano": {"input": 0.000025, "output": 0.00005},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4o": {"input": 0.005, "output": 0.0015},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    }
    
    def __init__(
        self,
        api_token: str,
        model: str = "gpt-5-nano",
        api_url: str = "https://api.openai.com/v1/chat/completions",
        min_length: int = 1,
        max_length: int = 5000,
        rate_limit: str = "10/m",
        max_cost: float = 0.0,
        cost_warning_threshold: float = 1.0
    ):
        """
        Initialize the LLM translator
        
        Args:
            api_token: API token for authentication
            model: LLM model to use (default: gpt-5-nano)
            api_url: API endpoint URL
            min_length: Minimum text length to translate
            max_length: Maximum text length to translate
            rate_limit: Rate limit in format "num/unit" (e.g., "10/m" for 10 per minute)
        """
        self.api_token = api_token
        self.model = model
        self.api_url = api_url
        self.min_length = min_length
        self.max_length = max_length
        self.rate_limit = rate_limit
        self.request_history = []
        self._rate_limit_lock = threading.Lock()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._parse_rate_limit()
        
        # Cost tracking and control
        self._cost_lock = threading.Lock()
        self.total_tokens = {"input": 0, "output": 0, "total": 0}
        self.total_cost = 0.0
        self.request_count = 0
        self.success_count = 0
        self.fail_count = 0
        self.max_cost = max_cost
        self.cost_warning_threshold = cost_warning_threshold
        self._warning_shown = False
        
    def _parse_rate_limit(self) -> None:
        """Parse the rate limit string into number and unit"""
        if self.rate_limit:
            num, unit = self.rate_limit.split('/')
            self.rate_limit_num = int(num)
            if unit == 's':
                self.rate_limit_seconds = 1
            elif unit == 'm':
                self.rate_limit_seconds = 60
            elif unit == 'h':
                self.rate_limit_seconds = 3600
            else:
                raise ValueError(f"Unsupported rate limit unit: {unit}")
        else:
            self.rate_limit_num = None
            self.rate_limit_seconds = None
            
    def _check_rate_limit(self) -> None:
        """Check if the rate limit is exceeded and wait if necessary (thread-safe)."""
        if not self.rate_limit_num:
            return

        while True:
            with self._rate_limit_lock:
                current_time = time.time()
                # Remove old requests outside the time window
                self.request_history = [
                    t for t in self.request_history
                    if current_time - t < self.rate_limit_seconds
                ]

                if len(self.request_history) < self.rate_limit_num:
                    self.request_history.append(current_time)
                    return

                sleep_time = self.rate_limit_seconds - (current_time - self.request_history[0]) + 0.1
                queue_depth = len(self.request_history)

            if sleep_time > 0:
                self.logger.info(
                    f"Rate limit queue wait: depth={queue_depth}, sleep={sleep_time:.2f}s"
                )
                time.sleep(sleep_time)
            else:
                # Avoid busy loop caused by timing precision at window boundary.
                time.sleep(0.05)
    
    def translate(
        self,
        text: str,
        target_language: str,
        system_prompt: str,
        user_prompt: str
    ) -> Optional[str]:
        """
        Translate text to target language using LLM
        
        Args:
            text: Text to translate
            target_language: Target language code
            system_prompt: System prompt for the LLM
            user_prompt: User prompt with context
            
        Returns:
            Translated text or None if translation fails
        """
        if not self.api_token:
            raise ValueError("API token is required")
            
        # Check if translation should proceed (includes empty text check and cost limit)
        if not self.should_translate(text):
            if not text or len(text.strip()) == 0:
                self.logger.debug("Empty text, skipping translation")
            return text
        
        # Check text length
        if len(text) < self.min_length:
            self.logger.debug(f"Text too short ({len(text)} < {self.min_length}), returning as-is")
            return text
            
        if len(text) > self.max_length:
            self.logger.warning(f"Text too long ({len(text)} > {self.max_length}), truncating")
            text = text[:self.max_length]
        
        # Check rate limit before making request
        self._check_rate_limit()
        
        # Prepare API request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_token}"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        }
        
        try:
            self.logger.debug(f"Translating to {target_language}: {text[:50]}...")
            response = requests.post(
                self.api_url,
                headers=headers,
                data=json.dumps(data),
                timeout=30
            )
            
            # Track request count
            with self._cost_lock:
                self.request_count += 1
            
            if response.status_code == 200:
                response_data = response.json()
                translated_text = response_data['choices'][0]['message']['content'].strip()
                
                # Track token usage and cost
                usage = response_data.get('usage', {})
                if usage:
                    input_tokens = usage.get('prompt_tokens', 0)
                    output_tokens = usage.get('completion_tokens', 0)
                    total_tokens = usage.get('total_tokens', input_tokens + output_tokens)
                    
                    with self._cost_lock:
                        self.total_tokens['input'] += input_tokens
                        self.total_tokens['output'] += output_tokens
                        self.total_tokens['total'] += total_tokens
                        self.success_count += 1
                        
                        # Calculate cost
                        price = self.MODEL_PRICES.get(self.model, {"input": 0, "output": 0})
                        cost = (input_tokens * price['input'] + output_tokens * price['output']) / 1000
                        self.total_cost += cost
                        
                        self.logger.info(
                            f"Token usage: input={input_tokens}, output={output_tokens}, "
                            f"total={total_tokens}, cost=${cost:.6f}"
                        )
                else:
                    # No usage data in response, log warning
                    with self._cost_lock:
                        self.success_count += 1
                    self.logger.warning("No usage data in API response, cannot track tokens")
                
                self.logger.debug(f"Translation successful: {text[:30]}... -> {translated_text[:30]}...")
                return translated_text
            else:
                with self._cost_lock:
                    self.fail_count += 1
                self.logger.error(
                    f"Translation failed with status {response.status_code}: {response.text}"
                )
                return None
                
        except requests.RequestException as e:
            with self._cost_lock:
                self.fail_count += 1
            self.logger.error(f"Request failed: {e}")
            return None
        except (KeyError, IndexError) as e:
            with self._cost_lock:
                self.fail_count += 1
            self.logger.error(f"Failed to parse response: {e}")
            return None
    
    def get_cost_summary(self) -> str:
        """Return a human-readable cost summary"""
        with self._cost_lock:
            return (
                f"\n{'='*60}\n"
                f"TRANSLATION COST SUMMARY\n"
                f"{'='*60}\n"
                f"Model: {self.model}\n"
                f"Total Requests: {self.request_count}\n"
                f"Successful: {self.success_count}\n"
                f"Failed: {self.fail_count}\n"
                f"Success Rate: {self.success_count/max(1,self.request_count)*100:.1f}%\n"
                f"\nToken Usage:\n"
                f"  Input tokens:  {self.total_tokens['input']:,}\n"
                f"  Output tokens: {self.total_tokens['output']:,}\n"
                f"  Total tokens:  {self.total_tokens['total']:,}\n"
                f"\nEstimated Cost: ${self.total_cost:.4f} USD\n"
                f"{'='*60}\n"
            )
    
    def get_cost_summary_dict(self) -> dict:
        """Return cost summary as dictionary for programmatic access"""
        with self._cost_lock:
            return {
                "model": self.model,
                "request_count": self.request_count,
                "success_count": self.success_count,
                "fail_count": self.fail_count,
                "success_rate": self.success_count/max(1,self.request_count)*100,
                "input_tokens": self.total_tokens['input'],
                "output_tokens": self.total_tokens['output'],
                "total_tokens": self.total_tokens['total'],
                "estimated_cost_usd": self.total_cost,
            }
    
    def check_cost_limit(self) -> bool:
        """
        Check if cost limit is exceeded.
        
        Returns:
            True if within limits, False if exceeded
        """
        if self.max_cost <= 0:
            return True  # No limit set
        
        with self._cost_lock:
            if self.total_cost > self.max_cost:
                self.logger.error(
                    f"Cost limit exceeded! Current: ${self.total_cost:.4f}, "
                    f"Limit: ${self.max_cost:.2f}"
                )
                return False
            
            # Check warning threshold
            if not self._warning_shown and self.total_cost > self.cost_warning_threshold:
                self.logger.warning(
                    f"⚠️ Cost warning: Current cost ${self.total_cost:.4f} "
                    f"exceeds threshold ${self.cost_warning_threshold:.2f}"
                )
                self._warning_shown = True
            
            return True
    
    def should_translate(self, text: str) -> bool:
        """
        Check if translation should proceed based on cost limits.
        
        Args:
            text: Text to be translated
            
        Returns:
            True if translation can proceed, False otherwise
        """
        # Skip empty text
        if not text or len(text.strip()) == 0:
            return False
        
        # Check cost limit before making API call
        if not self.check_cost_limit():
            return False
        
        return True
