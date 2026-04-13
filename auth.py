import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from config import ACCOUNTS, TOKENS_DIR

SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']


def get_token(account_email: str):
    os.makedirs(TOKENS_DIR, exist_ok=True)
    token_path = os.path.join(TOKENS_DIR, f"{account_email}.pickle")
    creds = None

    if os.path.exists(token_path):
        with open(token_path, 'rb') as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES)
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
            auth_url, _ = flow.authorization_url(prompt='consent')
            print(f"\n  Открой эту ссылку в браузере ADS Power:\n  {auth_url}\n")
            code = input("  Вставь код из браузера: ")
            flow.fetch_token(code=code)
            creds = flow.credentials

        with open(token_path, 'wb') as f:
            pickle.dump(creds, f)

    print(f"  Токен сохранён: {token_path}")
    return creds


if __name__ == "__main__":
    print(f"Всего аккаунтов: {len(ACCOUNTS)}\n")
    for account in sorted(ACCOUNTS):
        print(f"→ Авторизуй аккаунт: {account}")
        answer = input("  Открой профиль в ADS Power и нажми Enter, или напиши 'skip' чтобы пропустить: ")
        if answer.strip().lower() == 'skip':
            print("  Пропущено.\n")
            continue
        get_token(account)
        print()
    print("Все токены получены!")
