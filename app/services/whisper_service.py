from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from groq import Groq

from app.config import GROQ_API_KEY, WHISPER_MODEL

logger = logging.getLogger(__name__)

# Límites whisper-large-v3-turbo (documentación Groq)
WHISPER_RPM_LIMIT = 20
WHISPER_RPD_LIMIT = 2000
WHISPER_ASH_LIMIT = 7200  # audio seconds per hour (7.2k)
WHISPER_ASD_LIMIT = 28800  # audio seconds per day (28.8k)

class WhisperService:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
        self.model = WHISPER_MODEL

        self.rpm_limit = WHISPER_RPM_LIMIT
        self.rpd_limit = WHISPER_RPD_LIMIT
        self.ash_limit = WHISPER_ASH_LIMIT
        self.asd_limit = WHISPER_ASD_LIMIT

        self.minute_requests = 0
        self.day_requests = 0
        self.hour_seconds = 0
        self.day_seconds = 0

        self.last_minute_reset = time.time()
        self.last_hour_reset = time.time()
        self.last_day_reset = datetime.utcnow().date()

        self.lock = threading.Lock()

        # Directorio para datos persistentes
        self.data_dir = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.counters_file = self.data_dir / "whisper_counters.json"

        # Cargar contadores desde archivo si existe
        print(f"[Whisper] INIT id={id(self)} data_dir={self.data_dir} counters_file={self.counters_file}")
        self.load_counters()
        print(f"[Whisper] AFTER LOAD id={id(self)} minute_requests={self.minute_requests} day_requests={self.day_requests} hour_seconds={self.hour_seconds} day_seconds={self.day_seconds}")

    def load_counters(self):
        """Load counters from JSON file if exists."""
        try:
            print(f"[Whisper] load_counters START, counters_file={self.counters_file}, exists={self.counters_file.exists()}")
            if self.counters_file.exists():
                with open(self.counters_file, "r") as f:
                    data = json.load(f)
                now = time.time()
                today = datetime.utcnow().date()
                self.minute_requests = data.get("minute_requests", 0)
                self.day_requests = data.get("day_requests", 0)
                self.hour_seconds = data.get("hour_seconds", 0.0)
                self.day_seconds = data.get("day_seconds", 0.0)
                self.last_minute_reset = data.get("last_minute_reset", now)
                self.last_hour_reset = data.get("last_hour_reset", now)
                last_day = data.get("last_day_reset", today.isoformat())
                print(f"[Whisper] load_counters raw: minute_requests={self.minute_requests}, day_requests={self.day_requests}, hour_seconds={self.hour_seconds}, day_seconds={self.day_seconds}, last_minute={self.last_minute_reset}, last_hour={self.last_hour_reset}, last_day={last_day}")
                if isinstance(last_day, str):
                    try:
                        self.last_day_reset = datetime.fromisoformat(last_day).date()
                    except Exception:
                        self.last_day_reset = today
                else:
                    self.last_day_reset = today
                print(f"[Whisper] load_counters loaded: minute_requests=%d, day_requests=%d, hour_seconds=%.2f, day_seconds=%.2f, last_minute_reset=%s, last_hour_reset=%s, last_day_reset=%s",
                      self.minute_requests, self.day_requests, self.hour_seconds, self.day_seconds, self.last_minute_reset, self.last_hour_reset, self.last_day_reset)
                logger.info("[Whisper] Counters loaded from %s: minute_requests=%d, day_requests=%d, hour_seconds=%.2f, day_seconds=%.2f",
                            self.counters_file, self.minute_requests, self.day_requests, self.hour_seconds, self.day_seconds)
            else:
                print("[Whisper] load_counters: counters file does not exist, starting fresh")
        except Exception as e:
            print(f"[Whisper] load_counters EXCEPTION: {e}")
            logger.error("[Whisper] Failed to load counters: %s. Starting fresh.", e)
            self.minute_requests = 0
            self.day_requests = 0
            self.hour_seconds = 0.0
            self.day_seconds = 0.0
            self.last_minute_reset = time.time()
            self.last_hour_reset = time.time()
            self.last_day_reset = datetime.utcnow().date()
            self.save_counters()
            print(f"[Whisper] load_counters after exception reset and saved: minute_requests={self.minute_requests}, day_requests={self.day_requests}, hour_seconds={self.hour_seconds}, day_seconds={self.day_seconds}")

    def save_counters(self):
        """Save counters to JSON file."""
        try:
            data = {
                "minute_requests": self.minute_requests,
                "day_requests": self.day_requests,
                "hour_seconds": self.hour_seconds,
                "day_seconds": self.day_seconds,
                "last_minute_reset": self.last_minute_reset,
                "last_hour_reset": self.last_hour_reset,
                "last_day_reset": self.last_day_reset.isoformat() if self.last_day_reset else None,
            }
            with open(self.counters_file, "w") as f:
                json.dump(data, f)
            print(f"[Whisper] save_counters: minute_requests={self.minute_requests}, day_requests={self.day_requests}, hour_seconds={self.hour_seconds}, day_seconds={self.day_seconds}")
        except Exception as e:
            print(f"[Whisper] save_counters EXCEPTION: {e}")
            logger.error("[Whisper] Failed to save counters: %s", e)

    def _reset_counters_if_needed(self):
        now = time.time()
        today = datetime.utcnow().date()
        with self.lock:
            print(f"[Whisper] _reset_counters_if_needed: minute_requests={self.minute_requests}, last_minute_reset={self.last_minute_reset}, now={now}, diff={now - self.last_minute_reset:.2f}s")
            print(f"[Whisper] _reset_counters_if_needed: hour_seconds={self.hour_seconds}, last_hour_reset={self.last_hour_reset}, diff_hour={(now - self.last_hour_reset)/3600:.2f}h")
            print(f"[Whisper] _reset_counters_if_needed: day_requests={self.day_requests}, last_day_reset={self.last_day_reset}, today={today}")
            reset = False
            if now - self.last_minute_reset >= 60:
                print(f"[Whisper] Resetting minute_requests to 0")
                self.minute_requests = 0
                self.last_minute_reset = now
                reset = True
            if now - self.last_hour_reset >= 3600:
                print(f"[Whisper] Resetting hour_seconds to 0")
                self.hour_seconds = 0
                self.last_hour_reset = now
                reset = True
            if today != self.last_day_reset:
                print(f"[Whisper] Resetting day_requests and day_seconds to 0")
                self.day_requests = 0
                self.day_seconds = 0
                self.last_day_reset = today
                reset = True
            if reset:
                self.save_counters()

    def _increment_usage(self, audio_seconds: float):
        with self.lock:
            self.minute_requests += 1
            self.day_requests += 1
            self.hour_seconds += audio_seconds
            self.day_seconds += audio_seconds
            # Persist counters immediately
            self.save_counters()

    def get_usage(self) -> dict:
        service_id = id(self)
        print(f"[Whisper] get_usage called, id={service_id}")
        print(f"[Whisper] BEFORE RESET: minute_requests={self.minute_requests}, day_requests={self.day_requests}, hour_seconds={self.hour_seconds}, day_seconds={self.day_seconds}")
        self._reset_counters_if_needed()
        with self.lock:
            usage = {
                "minute_requests": self.minute_requests,
                "day_requests": self.day_requests,
                "hour_seconds": self.hour_seconds,
                "day_seconds": self.day_seconds,
                "rpm_limit": self.rpm_limit,
                "rpd_limit": self.rpd_limit,
                "ash_limit": self.ash_limit,
                "asd_limit": self.asd_limit,
            }
            print(f"[Whisper] AFTER RESET: minute_requests={self.minute_requests}, day_requests={self.day_requests}, hour_seconds={self.hour_seconds}, day_seconds={self.day_seconds}")
            return usage

    def transcribe(self, audio_bytes: bytes, filename: str, duration_seconds: float) -> str:
        self._reset_counters_if_needed()
        if not self.client:
            raise RuntimeError("Groq client not configured")
        try:
            result = self.client.audio.transcriptions.create(
                file=(filename, audio_bytes),
                model=self.model,
            )
            text = result.text or ""
            self._increment_usage(duration_seconds)
            logger.debug("Whisper transcribed %.2fs: %s", duration_seconds, text)
            return text
        except Exception as e:
            logger.exception("Whisper transcription failed")
            raise
