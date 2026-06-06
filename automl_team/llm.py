"""Gemini wiring: .env loading, client factory, model config."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from google import genai

DEFAULT_MODEL = "gemini-2.5-flash"

load_dotenv()


def get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and fill in your key."
        )
    return genai.Client(api_key=api_key)


def get_model() -> str:
    return os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL
