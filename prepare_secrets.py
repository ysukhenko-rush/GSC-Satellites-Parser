"""
Утилита для подготовки секрета GSC_TOKENS_JSON перед загрузкой в GitHub.

Запускать локально ОДИН РАЗ после получения всех токенов через auth.py:
    python prepare_secrets.py

Выводит JSON-строку, которую нужно вставить в:
  GitHub → Settings → Secrets → GSC_TOKENS_JSON
"""

import os
import base64
import json

from config import TOKENS_DIR, ACCOUNTS

result = {}
missing = []

for account in sorted(ACCOUNTS):
    token_path = os.path.join(TOKENS_DIR, f"{account}.pickle")
    if os.path.exists(token_path):
        with open(token_path, 'rb') as f:
            result[account] = base64.b64encode(f.read()).decode()
    else:
        missing.append(account)

if missing:
    print("Не найдены токены для:")
    for m in missing:
        print(f"  {m}")
    print()

print("=== GSC_TOKENS_JSON (вставить в GitHub Secrets) ===")
print(json.dumps(result, ensure_ascii=False, indent=None))
