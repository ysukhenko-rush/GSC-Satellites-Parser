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
        need_new_auth = True
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                need_new_auth = False
            except Exception:
                print("  Токен протух и не рефрешится — нужна повторная авторизация.")

        if need_new_auth:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES)
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
            auth_url, _ = flow.authorization_url(prompt='consent')
            print(f"\n  Открой эту ссылку в браузере ADS Power:\n  {auth_url}\n")
            code = input("  Вставь код из браузера: ").strip()
            flow.fetch_token(code=code)
            creds = flow.credentials

        with open(token_path, 'wb') as f:
            pickle.dump(creds, f)

    print(f"  Токен сохранён: {token_path}")
    return creds


def token_is_valid(account_email: str) -> bool:
    token_path = os.path.join(TOKENS_DIR, f"{account_email}.pickle")
    if not os.path.exists(token_path):
        return False
    try:
        with open(token_path, 'rb') as f:
            creds = pickle.load(f)
        if creds.valid:
            return True
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, 'wb') as f:
                pickle.dump(creds, f)
            return True
    except Exception:
        pass
    return False


if __name__ == "__main__":
    need_auth = []
    ok = []

    for account in sorted(ACCOUNTS):
        if token_is_valid(account):
            ok.append(account)
        else:
            need_auth.append(account)

    if ok:
        print("Рабочие токены (пропускаем):")
        for a in ok:
            print(f"  ✓ {a}")
        print()

    if not need_auth:
        print("Все токены актуальны, ничего делать не нужно.")
    else:
        print(f"Нужна авторизация ({len(need_auth)} аккаунтов):")
        for a in need_auth:
            print(f"  ✗ {a}")
        print()
        for account in need_auth:
            print(f"→ Авторизуй аккаунт: {account}")
            answer = input("  Открой профиль в ADS Power и нажми Enter, или 'skip': ")
            if answer.strip().lower() == 'skip':
                print("  Пропущено.\n")
                continue
            get_token(account)
            print()
        print("Готово!")
