import os
import pickle
import datetime
import time
from urllib.parse import urlparse

from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from config import (
    DOMAIN_ACCOUNT_MAP,
    DOMAIN_ACCOUNT_MAP_PLATOV,
    DOMAIN_ACCOUNT_MAP_PRIME,
    DOMAIN_ACCOUNT_MAP_MIGHTYCALL,
    TOKENS_DIR,
)

SHEET_NAME = 'Метрики'
GSC_LAG_DAYS = 3
COLLECTION_DAYS_FALLBACK = [28, 21, 14, 7, 3]

PROJECTS = {
    'smsactivate': {
        'domain_map': DOMAIN_ACCOUNT_MAP,
        'spreadsheet_id': os.environ.get('SPREADSHEET_ID', '17u_jItYm8SgBtgO6Cck5gPCbAu_fL45lKhlguzkLzow'),
    },
    'platov': {
        'domain_map': DOMAIN_ACCOUNT_MAP_PLATOV,
        'spreadsheet_id': os.environ.get('SPREADSHEET_ID_PLATOV'),
    },
    'prime': {
        'domain_map': DOMAIN_ACCOUNT_MAP_PRIME,
        'spreadsheet_id': os.environ.get('SPREADSHEET_ID_PRIME'),
    },
    'mightycall': {
        'domain_map': DOMAIN_ACCOUNT_MAP_MIGHTYCALL,
        'spreadsheet_id': (
            os.environ.get('SPREADSHEET_ID_MIGHTYCALL')
            or '1YjzY6E8d-TRqS2_EzkTf-3hI9R4oISn6yfKKf_mks34'
        ),
    },
}


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


# Домен мог быть добавлен в Search Console и как domain-property (sc-domain:),
# и как URL-префикс (с/без www, http/https) — пробуем все варианты по очереди.
PROPERTY_URI_TEMPLATES = [
    "sc-domain:{domain}",
    "https://{domain}/",
    "https://www.{domain}/",
    "http://{domain}/",
    "http://www.{domain}/",
]


def resolve_property_uri(service, domain: str):
    """Пробует все варианты property URI одним лёгким запросом (rowLimit=1)
    и возвращает первый, к которому есть доступ у этого аккаунта.
    None, если ни один вариант не доступен."""
    end = datetime.date.today() - datetime.timedelta(days=GSC_LAG_DAYS)
    start = end - datetime.timedelta(days=28)
    for template in PROPERTY_URI_TEMPLATES:
        uri = template.format(domain=domain)
        try:
            service.searchanalytics().query(
                siteUrl=uri,
                body={
                    'startDate': str(start),
                    'endDate': str(end),
                    'dimensions': ['query'],
                    'rowLimit': 1,
                }
            ).execute()
            return uri
        except Exception:
            continue
    return None


def fetch_metrics(service, property_uri: str, start_date: str, end_date: str):
    """Возвращает (rows, error). error is None, если запрос к GSC прошёл успешно
    (то есть property_uri доступен под этим аккаунтом) — даже если rows пуст."""
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
        return response.get('rows', []), None
    except Exception as e:
        return [], e


def fetch_metrics_with_fallback(service, domain: str):
    """Сначала определяет, под каким property URI домен доступен этому аккаунту
    (domain-property или URL-префикс), затем пробует периоды 28→21→14→7→3 дня.
    Возвращает (rows, verified):
      rows — найденные строки метрик (может быть пустым списком)
      verified — True, если домен доступен этому аккаунту хоть в каком-то
                 виде (domain-property ИЛИ URL-префикс) — то есть реально
                 добавлен/подтверждён в Search Console под этим аккаунтом,
                 False — если недоступен вообще ни в одном варианте."""
    property_uri = resolve_property_uri(service, domain)
    if property_uri is None:
        print(f"    Домен недоступен этому аккаунту ни как sc-domain, ни как URL-префикс")
        return [], False, None

    is_url_prefix = property_uri != f"sc-domain:{domain}"
    if is_url_prefix:
        print(f"    Найден как URL-префикс свойство: {property_uri} (не как sc-domain — стоит пересоздать как domain-property)")

    for days in COLLECTION_DAYS_FALLBACK:
        start_date, end_date = get_date_range(days)
        rows, error = fetch_metrics(service, property_uri, start_date, end_date)
        if error is None:
            if rows:
                print(f"    Данные найдены за {days} дней ({start_date} → {end_date})")
                return rows, True, property_uri
            print(f"    Нет данных за {days} дней, пробуем меньше...")
        else:
            print(f"    Ошибка для {domain} ({property_uri}): {error}")
    print(f"    Данных нет даже за 3 дня (домен подтверждён, но метрик пока нет)")
    return [], True, property_uri


def collect_all(project: str, config: dict):
    domain_map = config['domain_map']
    spreadsheet_id = config['spreadsheet_id']

    if not spreadsheet_id:
        print(f"[{project}] Не задан SPREADSHEET_ID, пропуск")
        return

    # Подключение к Google Sheets через service account
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive',
    ]
    sheets_creds = ServiceAccountCredentials.from_json_keyfile_name(
        'sheets_service_account.json', scope)
    gc = gspread.authorize(sheets_creds)
    sheet = gc.open_by_key(spreadsheet_id).worksheet(SHEET_NAME)

    collection_date = str(datetime.date.today())
    print(f"[{project}] Дата запуска: {collection_date}  |  Периоды fallback: {COLLECTION_DAYS_FALLBACK} дней\n")

    all_rows = []
    services = {}       # кеш сервисов по аккаунту
    expired_accounts = set()  # аккаунты с протухшими токенами

    def placeholder_row(note: str):
        all_rows.append([
            domain_num, '', '', 0, 0, 0, 0, collection_date, '', note,
        ])

    for domain_num, info in sorted(domain_map.items()):
        account = info["account"]
        domain = info["domain"]
        print(f"  #{domain_num:>2}  {domain}  ({account})")

        try:
            if account not in services:
                if account in expired_accounts:
                    raise ValueError("token_expired")
                creds = load_creds(account)
                services[account] = build('searchconsole', 'v1', credentials=creds)

            rows, verified, property_uri = fetch_metrics_with_fallback(services[account], domain)
            url_prefix_note = (
                f'Найден как URL-префикс ({property_uri}), не как domain-property — стоит пересоздать в GSC'
                if property_uri and property_uri != f"sc-domain:{domain}" else ''
            )

            if rows:
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
                        '',
                        url_prefix_note,
                    ])
            elif verified:
                note = 'Домен подтверждён в GSC, метрик пока ещё нет'
                if url_prefix_note:
                    note += ' — ' + url_prefix_note
                placeholder_row(note)
            else:
                placeholder_row('Домен не найден/не подтверждён в Search Console под этим аккаунтом (ни sc-domain, ни URL-префикс)')
            time.sleep(1)  # защита от rate limit

        except FileNotFoundError:
            print(f"  Токен не найден для {account}, пропуск")
            expired_accounts.add(account)
            placeholder_row('Токен аккаунта не найден')
        except Exception as e:
            if 'invalid_grant' in str(e) or 'token_expired' in str(e):
                expired_accounts.add(account)
                print(f"  Токен протух для {account}, пропуск")
                placeholder_row('Токен аккаунта протух, нужна переавторизация')
            else:
                print(f"  Ошибка для {account}: {e}")
                placeholder_row(f'Ошибка сбора: {e}')

    if expired_accounts:
        warning = (
            f"⚠️ ОШИБКА СБОРА ДАННЫХ ({collection_date}): токены протухли для аккаунтов: "
            f"{', '.join(sorted(expired_accounts))}. "
            f"Нужно: 1) запустить python auth.py локально  "
            f"2) запустить python prepare_secrets.py  "
            f"3) обновить секрет GSC_TOKENS_JSON в GitHub → Settings → Secrets"
        )
        # Пишем предупреждение в колонку I (за пределами данных A-H), строка 1
        sheet.update("I1", [[warning]], value_input_option='RAW')
        sheet.format("I1", {
            "backgroundColor": {"red": 1.0, "green": 0.8, "blue": 0.8},
            "textFormat": {"bold": True}
        })
        print(f"\n⚠️  Предупреждение записано в таблицу (I1): {warning}")
    else:
        # Очищаем предупреждение если всё ок
        sheet.update("I1", [[""]], value_input_option='RAW')

    if all_rows:
        existing_rows = len(sheet.get_all_values()) - 1
        if existing_rows > 0:
            clear_range = f"A2:J{existing_rows + 1}"
            sheet.batch_clear([clear_range])
            print(f"Очищено строк в A-J: {existing_rows}")

        sheet.update(f"A2:J{len(all_rows) + 1}", all_rows, value_input_option='RAW')
        print(f"Записано строк: {len(all_rows)}")
    else:
        if not expired_accounts:
            print("\nНет данных для записи")


if __name__ == "__main__":
    for project_name, project_config in PROJECTS.items():
        collect_all(project_name, project_config)
