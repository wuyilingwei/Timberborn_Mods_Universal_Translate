"""
Translator module for Timberborn mods translation
Adapted from https://github.com/wuyilingwei/Timberborn_Tools
"""
import time
import json
import logging
import requests
from typing import Optional


class TranslatorLLM:
    """
    OPENAI-STYLED LLM API Translator with rate limiting
    """
    
    def __init__(
        self,
        api_token: str,
        model: str = "gpt-4o-mini",
        api_url: str = "https://api.openai.com/v1/chat/completions",
        min_length: int = 1,
        max_length: int = 5000,
        rate_limit: str = "10/m"
    ):
        """
        Initialize the LLM translator
        
        Args:
            api_token: API token for authentication
            model: LLM model to use (default: gpt-4o-mini)
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
        self.logger = logging.getLogger(self.__class__.__name__)
        self._parse_rate_limit()
        
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
        """Check if the rate limit is exceeded and wait if necessary"""
        if not self.rate_limit_num:
            return
            
        current_time = time.time()
        # Remove old requests outside the time window
        self.request_history = [
            t for t in self.request_history 
            if current_time - t < self.rate_limit_seconds
        ]
        
        # If we've hit the limit, wait
        if len(self.request_history) >= self.rate_limit_num:
            sleep_time = self.rate_limit_seconds - (current_time - self.request_history[0]) + 0.1
            if sleep_time > 0:
                self.logger.info(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
                # Clean up again after sleeping
                current_time = time.time()
                self.request_history = [
                    t for t in self.request_history 
                    if current_time - t < self.rate_limit_seconds
                ]
    
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
            
        # Check text length
        if not text or len(text.strip()) == 0:
            self.logger.warning("Empty text provided")
            return text
            
        if len(text) < self.min_length:
            self.logger.debug(f"Text too short ({len(text)} < {self.min_length}), returning as-is")
            return text
            
        if len(text) > self.max_length:
            self.logger.warning(f"Text too long ({len(text)} > {self.max_length}), truncating")
            text = text[:self.max_length]
        
        # Check rate limit before making request
        self._check_rate_limit()
        self.request_history.append(time.time())
        
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
            
            if response.status_code == 200:
                response_data = response.json()
                translated_text = response_data['choices'][0]['message']['content'].strip()
                self.logger.info(f"Translation successful: {text[:30]}... -> {translated_text[:30]}...")
                return translated_text
            else:
                self.logger.error(
                    f"Translation failed with status {response.status_code}: {response.text}"
                )
                return None
                
        except requests.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            return None
        except (KeyError, IndexError) as e:
            self.logger.error(f"Failed to parse response: {e}")
            return None
