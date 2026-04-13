TOKENS_DIR = 'tokens'

DOMAIN_ACCOUNT_MAP = {
    1:  {"domain": "smsactivate.biz",               "account": "y.sukhenko@rush-agency.ru"},
    2:  {"domain": "sms-activate.us.com",            "account": "rshcorporate5@gmail.com"},
    3:  {"domain": "smsactivate2.com",               "account": "rshcorporate6@gmail.com"},
    4:  {"domain": "smsactivate.name",               "account": "rshcorporate7@gmail.com"},
    5:  {"domain": "smsactivate.media",              "account": "rshcorporate5@gmail.com"},
    6:  {"domain": "sms-activate-alternatives.com",  "account": "rshcorporate6@gmail.com"},
    7:  {"domain": "smsactivate.me",                 "account": "rshcorporate7@gmail.com"},
    8:  {"domain": "smsactivate.info",               "account": "rshcorporate7@gmail.com"},
    9:  {"domain": "smsactivate2.us",                "account": "y.sukhenko@rush-agency.ru"},
    10: {"domain": "smsactivate5.com",               "account": "y.sukhenko@rush-agency.ru"},
    11: {"domain": "smsactivate.live",               "account": "rshcorporate4@gmail.com"},
    12: {"domain": "sms-activate.live",              "account": "rshcorporate4@gmail.com"},
    13: {"domain": "smsactivate.guru",               "account": "rshcorporate5@gmail.com"},
    14: {"domain": "sms-activate-login.com",         "account": "rshcorporate6@gmail.com"},
    15: {"domain": "smsactivate.pro",                "account": "rshcorporate10@gmail.com"},
    16: {"domain": "sms-activate.us",                "account": "rshcorporate10@gmail.com"},
    17: {"domain": "smsactivate.us",                 "account": "rshcorporate10@gmail.com"},
    18: {"domain": "smsactivate.es",                 "account": "rshcorporate4@gmail.com"},
    19: {"domain": "best-otp-services.com",          "account": "rshcorporate9@gmail.com"},
    20: {"domain": "sms-activate-service.com.br",    "account": "stiveneight@gmail.com"},
    21: {"domain": "sms-activate-login.com.br",      "account": "stiveneight@gmail.com"},
    22: {"domain": "smsactivate3.com",               "account": "rshcorporate9@gmail.com"},
    23: {"domain": "smsactivate1.biz",               "account": "rshcorporate9@gmail.com"},
    24: {"domain": "smsactivate.us.com",             "account": "rshcorporate1@gmail.com"},
    25: {"domain": "smsactivate1.us.com",            "account": "rshcorporate1@gmail.com"},
    26: {"domain": "smsactivate.vip",                "account": "rshcorporate1@gmail.com"},
    27: {"domain": "smsactivate.mx",                 "account": "rshcorporate3@gmail.com"},
    # 28: best-sms-services.com  — аккаунт неизвестен, пропуск
    # 29: top-sms-services.com   — аккаунт неизвестен, пропуск
    30: {"domain": "sms-activator.biz",              "account": "rshcorporate3@gmail.com"},
}

ACCOUNTS = list(set(v["account"] for v in DOMAIN_ACCOUNT_MAP.values()))
