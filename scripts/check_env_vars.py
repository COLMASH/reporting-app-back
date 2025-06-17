#!/usr/bin/env python3
"""Check environment variables loading"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.config import settings

print("🔍 Checking environment variables...\n")

# Check raw env
print("Raw environment variable:")
print(f"DATABASE_URL from env: {os.getenv('DATABASE_URL')}")

print("\nSettings loaded by Pydantic:")
print(f"settings.database_url: {settings.database_url}")

print("\nOther settings:")
print(f"settings.debug: {settings.debug}")
print(f"settings.environment: {settings.environment}")
print(f"settings.jwt_secret: {settings.jwt_secret}")