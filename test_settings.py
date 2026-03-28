"""
Test settings loading
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.config.settings import settings

print(f"LLM_PROVIDER: {settings.LLM_PROVIDER}")
print(f"LLM_MODEL: {settings.LLM_MODEL}")
print(f"LLM_API_KEY: {settings.LLM_API_KEY[:20]}...")
print(f"LLM_API_BASE: {settings.LLM_API_BASE}")
