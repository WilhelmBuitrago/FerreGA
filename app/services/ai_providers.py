# app/services/ai_providers.py
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Any, Dict, List
from groq import Groq
import requests

from app.config import GROQ_MODEL

logger = logging.getLogger(__name__)

class Provider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, api_key: str, model: str, counters_file: Path):
        self.api_key = api_key
        self.model = model
        self.counters_file = counters_file
        self.counters = self._load_counters()
        self.lock = threading.Lock()
        self.last_minute_reset = time.time()
        self.last_day_reset = datetime.utcnow().date()
        self.rpm_limit = None
        self.rpd_limit = None
        self.tpd_limit = None

    def _load_counters(self):
        try:
            if self.counters_file.exists():
                with open(self.counters_file, "r") as f:
                    data = json.load(f)
                # Ensure keys exist
                for k in ["minute_requests", "day_requests", "day_tokens", "last_minute_reset", "last_day_reset"]:
                    if k not in data:
                        if k == "last_minute_reset":
                            data[k] = time.time()
                        elif k == "last_day_reset":
                            data[k] = datetime.utcnow().date().isoformat()
                        else:
                            data[k] = 0
                return data
        except Exception as e:
            logger.error(f"[Provider] Failed to load counters: {e}")
        # default
        return {
            "minute_requests": 0,
            "day_requests": 0,
            "day_tokens": 0,
            "last_minute_reset": time.time(),
            "last_day_reset": datetime.utcnow().date().isoformat()
        }

    def _save_counters(self):
        try:
            with open(self.counters_file, "w") as f:
                json.dump(self.counters, f, indent=2)
        except Exception as e:
            logger.error(f"[Provider] Failed to save counters: {e}")

    def _reset_counters_if_needed(self):
        now = time.time()
        today = datetime.utcnow().date()
        with self.lock:
            # Reset minute
            last_min = self.counters.get("last_minute_reset", 0)
            if now - last_min >= 60:
                self.counters["minute_requests"] = 0
                self.counters["last_minute_reset"] = now
                self._save_counters()
            # Reset day
            last_day_str = self.counters.get("last_day_reset", today.isoformat())
            try:
                last_day = datetime.fromisoformat(last_day_str).date()
            except Exception:
                last_day = today
            if today != last_day:
                self.counters["day_requests"] = 0
                self.counters["day_tokens"] = 0
                self.counters["last_day_reset"] = today.isoformat()
                self._save_counters()

    def _increment_usage(self, prompt_tokens, completion_tokens):
        with self.lock:
            self.counters["minute_requests"] += 1
            self.counters["day_requests"] += 1
            self.counters["day_tokens"] += prompt_tokens + completion_tokens
            self._save_counters()

    def get_usage(self):
        self._reset_counters_if_needed()
        with self.lock:
            return {
                "minute_requests": self.counters["minute_requests"],
                "day_requests": self.counters["day_requests"],
                "day_tokens": self.counters["day_tokens"],
                "rpm_limit": self.rpm_limit,
                "rpd_limit": self.rpd_limit,
                "tpd_limit": self.tpd_limit,
            }

    @abstractmethod
    def call_chat_completion(self, messages, tools=None, tool_choice=None):
        """Synchronous call to the model. Returns a response object with attributes:
        - choices: list with first element having .message
          .message.role, .message.content, .message.tool_calls (list with .id, .function.name, .function.arguments)
        - usage: .prompt_tokens, .completion_tokens
        """
        pass


class GroqProvider(Provider):
    def __init__(self, api_key: str, model: str):
        data_dir = Path(__file__).parent.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        counters_file = data_dir / "ai_counters_groq.json"
        super().__init__(api_key, model, counters_file)
        self.client = Groq(api_key=api_key)
        self.rpm_limit = 30
        self.rpd_limit = 1000
        self.tpd_limit = 100000

    def call_chat_completion(self, messages, tools=None, tool_choice=None):
        self._reset_counters_if_needed()
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 800,
            }
            # Si hay herramientas, no usar response_format (incompatible)
            if tools is not None:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = tool_choice if tool_choice is not None else "auto"
            else:
                kwargs["response_format"] = {"type": "json_object"}
            response = self.client.chat.completions.create(**kwargs)
            usage = getattr(response, 'usage', None)
            if usage:
                self._increment_usage(getattr(usage, 'prompt_tokens', 0), getattr(usage, 'completion_tokens', 0))
            return response
        except Exception as e:
            logger.error(f"[GroqProvider] API error: {e}")
            raise


class NvidiaProvider(Provider):
    def __init__(self, api_key: str, model: str, base_url: str = "https://integrate.api.nvidia.com/v1/chat/completions"):
        data_dir = Path(__file__).parent.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        counters_file = data_dir / "ai_counters_nvidia.json"
        super().__init__(api_key, model, counters_file)
        self.base_url = base_url
        self.rpm_limit = 40
        self.rpd_limit = 0  # No daily limit
        self.tpd_limit = 0  # No TPD limit

    def call_chat_completion(self, messages, tools=None, tool_choice=None):
        self._reset_counters_if_needed()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 16384,
            "temperature": 0.1,
            "top_p": 0.95,
            "stream": False,
        }
        if tools is not None:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice if tool_choice is not None else "auto"
        try:
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=120)
            if response.status_code != 200:
                logger.error(f"[NvidiaProvider] HTTP {response.status_code}: {response.text}")
                response.raise_for_status()
            resp_json = response.json()
            # Convert to Groq-like response object
            class Message:
                def __init__(self, role, content, tool_calls=None):
                    self.role = role
                    self.content = content
                    self.tool_calls = tool_calls or []
                    self.function_call = None
            class Choice:
                def __init__(self, message, finish_reason="stop"):
                    self.message = message
                    self.finish_reason = finish_reason
            class Usage:
                def __init__(self, prompt_tokens, completion_tokens):
                    self.prompt_tokens = prompt_tokens
                    self.completion_tokens = completion_tokens
                    self.total_tokens = prompt_tokens + completion_tokens
            class Response:
                def __init__(self, choices, usage, model):
                    self.choices = choices
                    self.usage = usage
                    self.model = model

            choice_data = resp_json["choices"][0]
            msg_data = choice_data["message"]
            tool_calls = []
            if "tool_calls" in msg_data and msg_data["tool_calls"]:
                for tc in msg_data["tool_calls"]:
                    if tc.get("type") == "function":
                        args = tc["function"]["arguments"]
                        if isinstance(args, dict):
                            args = json.dumps(args)
                        tool_calls.append(type('ToolCall', (), {
                            'id': tc.get("id", ""),
                            'type': 'function',
                            'function': type('Function', (), {
                                'name': tc["function"]["name"],
                                'arguments': args
                            })
                        }))
            message = Message(
                role=msg_data["role"],
                content=msg_data.get("content", ""),
                tool_calls=tool_calls
            )
            choices = [Choice(message, choice_data.get("finish_reason", "stop"))]
            usage_data = resp_json.get("usage", {})
            usage = Usage(usage_data.get("prompt_tokens", 0), usage_data.get("completion_tokens", 0))
            response_obj = Response(choices, usage, resp_json.get("model", self.model))
            self._increment_usage(usage.prompt_tokens, usage.completion_tokens)
            return response_obj
        except Exception as e:
            logger.error(f"[NvidiaProvider] API error: {e}")
            raise
