import os
import pickle
import datetime
import time
from urllib.parse import urlparse

from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from config import DOMAIN_ACCOUNT_MAP_PLATOV, TOKENS_DIR

SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID_PLATOV')
SHEET_NAME = 'Метрики'

# GSC лагает ~3 дня; пробуем периоды по убыванию пока не найдём данные
COLLECTION_DAYS_FALLBACK = [28, 21, 14, 7, 3]
GSC_LAG_DAYS = 3


def get_date_range(days: int):
    end = datetime.date.today() - datetime.timedelta(days=GSC_LAG_DAYS)
    start = end - datetime.timedelta(days=days)
    return str(start), str(end)


def load_creds(account_email: str):
    token_path = os.path.join(TOKENS_DIR, f"{account_email}.pickle")
    with open(token_path, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def fetch_metrics(service, domain: str, start_date: str, end_date: str) -> list:
    property_uri = f"sc-domain:{domain}"
    try:
        response = service.searchanalytics().query(
            siteUrl=property_uri,
            body={
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': ['query', 'page'],
                'rowLimit': 1000,
            }
        ).execute()
        return response.get('rows', [])
    except Exception as e:
        print(f"    Ошибка для {domain}: {e}")
        return []


def fetch_metrics_with_fallback(service, domain: str) -> tuple[list, int]:
    """Пробует периоды 28→21→14→7→3 дня, возвращает (rows, использованный_период)."""
    for days in COLLECTION_DAYS_FALLBACK:
        start_date, end_date = get_date_range(days)
        rows = fetch_metrics(service, domain, start_date, end_date)
        if rows:
            print(f"    Данные найдены за {days} дней ({start_date} → {end_date})")
            return rows, days
        else:
            print(f"    Нет данных за {days} дней, пробуем меньше...")
    print(f"    Данных нет даже за 3 дня")
    return [], 0


def collect_all():
    # Подключение к Google Sheets через service account
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive',
    ]
    sheets_creds = ServiceAccountCredentials.from_json_keyfile_name(
        'sheets_service_account.json', scope)
    gc = gspread.authorize(sheets_creds)
    sheet = gc.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)

    collection_date = str(datetime.date.today())
    print(f"[platov.co] Дата запуска: {collection_date}  |  Периоды fallback: {COLLECTION_DAYS_FALLBACK} дней\n")

    all_rows = []
    services = {}  # кеш сервисов по аккаунту

    for domain_num, info in sorted(DOMAIN_ACCOUNT_MAP_PLATOV.items()):
        account = info["account"]
        domain = info["domain"]
        print(f"  #{domain_num:>2}  {domain}  ({account})")

        try:
            if account not in services:
                creds = load_creds(account)
                services[account] = build('searchconsole', 'v1', credentials=creds)

            rows, used_days = fetch_metrics_with_fallback(services[account], domain)

            for row in rows:
                keys = row.get('keys', [])
                keyword = keys[0] if keys else ''
                raw_page = keys[1] if len(keys) > 1 else ''
                path = urlparse(raw_page).path
                page = 'главная' if not path or path == '/' else path
                all_rows.append([
                    domain_num,
                    page,
                    keyword,
                    row.get('clicks', 0),
                    row.get('impressions', 0),
                    round(row.get('ctr', 0) * 100, 2),
                    round(row.get('position', 0), 1),
                    collection_date,
                ])
            time.sleep(1)  # защита от rate limit

        except FileNotFoundError:
            print(f"  Токен не найден для {account}, пропуск")
        except Exception as e:
            print(f"  Ошибка для {account}: {e}")

    if all_rows:
        existing_rows = len(sheet.get_all_values()) - 1
        if existing_rows > 0:
            clear_range = f"A2:H{existing_rows + 1}"
            sheet.batch_clear([clear_range])
            print(f"Очищено строк в A-H: {existing_rows}")

        sheet.update(f"A2:H{len(all_rows) + 1}", all_rows, value_input_option='RAW')
        print(f"Записано строк: {len(all_rows)}")
    else:
        print("\nНет данных для записи")


if __name__ == "__main__":
    collect_all()
