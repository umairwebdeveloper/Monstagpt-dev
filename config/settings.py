import os
from datetime import timedelta
from distutils.util import strtobool

from celery.schedules import crontab

LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")

SECRET_KEY = os.getenv("SECRET_KEY", None)

# SERVER_NAME = os.getenv(
#     "SERVER_NAME", "localhost:{0}".format(os.getenv("PORT", "8000"))
# )

# SERVER_NAME = 'localhost'

# SQLAlchemy.
pg_user = os.getenv("POSTGRES_USER", "monstagpt")
pg_pass = os.getenv("POSTGRES_PASSWORD", "password")
pg_host = os.getenv("POSTGRES_HOST", "postgres")
pg_port = os.getenv("POSTGRES_PORT", "5432")
pg_db = os.getenv("POSTGRES_DB", pg_user)
db = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", db)

# Redis.
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Celery.
CELERY_CONFIG = {
    "broker_url": REDIS_URL,
    "result_backend": REDIS_URL,
    "include": [
        "monstagpt.blueprints.contact.tasks",
        "monstagpt.blueprints.user.tasks",
        "monstagpt.blueprints.billing.tasks",
        "monstagpt.blueprints.gpt.tasks",
        "monstagpt.blueprints.ignite.tasks",
        "monstagpt.blueprints.stripe_payments.tasks"
    ],
"task_routes": {
        'monstagpt.blueprints.contact.tasks.*': {'queue': 'queue1'},
        'monstagpt.blueprints.user.tasks.*': {'queue': 'queue1'},
        'monstagpt.blueprints.billing.tasks.*': {'queue': 'queue1'},
        'monstagpt.blueprints.gpt.tasks.*': {'queue': 'queue2'},
        'monstagpt.blueprints.ignite.tasks.*': {'queue': 'queue2'},

},
}

# Flask-Mail.
MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = os.getenv("MAIL_PORT", 587)
MAIL_USE_TLS = bool(strtobool(os.getenv("MAIL_USE_TLS", "true")))
MAIL_USE_SSL = bool(strtobool(os.getenv("MAIL_USE_SSL", "false")))
MAIL_USERNAME = os.getenv("MAIL_USERNAME", None)
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", None)
MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "contact@local.host")
MAIL_DEFAULT_TO = os.getenv("MAIL_DEFAULT_TO", "contact@local.host")

# slack webhook url
SLACK_CRITICAL_WEBHOOK_URL = os.getenv("SLACK_CRITICAL_WEBHOOK_URL","https://")
SLACK_FEEDBACK_WEBHOOK_URL = os.getenv("SLACK_FEEDBACK_WEBHOOK_URL","https://")
SLACK_GENERAL_WEBHOOK_URL = os.getenv("SLACK_GENERAL_WEBHOOK_URL","https://")
SLACK_SUPPORT_WEBHOOK_URL = os.getenv("SLACK_SUPPORT_WEBHOOK_URL","https://")

# Flask-Babel.
LANGUAGES = {"en": "English", "kl": "Klingon", "es": "Spanish"}
BABEL_DEFAULT_LOCALE = "en"

# User.
SEED_ADMIN_USERNAME = os.getenv("SEED_ADMIN_USERNAME", "administrator")
SEED_ADMIN_EMAIL = os.getenv("SEED_ADMIN_EMAIL", "dev@local.host")
SEED_ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "password")
REMEMBER_COOKIE_DURATION = timedelta(days=90)

# Billing.
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", None)
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", None)
STRIPE_API_VERSION = "2022-08-01"
STRIPE_CURRENCY = "usd"
STRIPE_TRIAL_PERIOD_DAYS = 0
STRIPE_PLANS = {
     "0": {
        "id": "free",
        "name": "free",
        "amount": 0,
        "currency": STRIPE_CURRENCY,
        "interval": "month",
        "interval_count": 1,
        "statement_descriptor": "MONSTAGPT FREE",
        "metadata": {"coins": 0},
    },
     
    "1": {
        "id": "bronze",
        "name": "Bronze",
        "amount": 9900,
        "currency": STRIPE_CURRENCY,
        "interval": "month",
        "interval_count": 1,
        "statement_descriptor": "MONSTAGPT BRONZE",
        "metadata": {"coins": 100},
    },
    
    "2": {
        "id": "gold",
        "name": "Gold",
        "amount": 24900,
        "currency": STRIPE_CURRENCY,
        "interval": "month",
        "interval_count": 1,
        "statement_descriptor": "MONSTAGPT GOLD",
        "metadata": {"coins": 300, "recommended": True},
    },
    
    "3": {
        "id": "platinum",
        "name": "Platinum",
        "amount": 49900,
        "currency": STRIPE_CURRENCY,
        "interval": "month",
        "interval_count": 1,
        "statement_descriptor": "MONSTAGPT PLATINUM",
        "metadata": {"coins": 700},
    },  
}

# When a user change plan, I want to make sure that they aren't given more coins if they downgrade, so I 
# Included a plan weight so that I can check this.
# mode can be either payment or subscription
STRIPE_GPT_PLANS = {
    'gpt_bronze':{'price_id':'price_1PJYPOEr99ZAPva5mGfiHNUh','mode':'subscription','coins':100,'plan_weight':1},
    'gpt_gold':{'price_id':'price_1PJYUCEr99ZAPva5S4Mcynv9','mode':'subscription','coins':300,'plan_weight':2},
    'gpt_platinum':{'price_id':'price_1PJYVkEr99ZAPva5Dk68XuHq','mode':'subscription','coins':700,'plan_weight':3},
    'gpt_tokens':{'price_id':'price_1PJa1oEr99ZAPva5z8TNkasw','mode':'payment','coins':10,'plan_weight':0},
}

PRICING_DATA = {
    "tiers": ["Free","Basic", "Standard", "Professional", "Enterprise"],
    "monthly_prices": ["0","99", "249", "499", "Contact Us"],
    "price_id": ['n/a','price_1PJYPOEr99ZAPva5mGfiHNUh','price_1PJYUCEr99ZAPva5S4Mcynv9','price_1PJYVkEr99ZAPva5Dk68XuHq','price_enterprise'],
    "mode": ['n/a','subscription','subscription','subscription','subscription'],
    "coins": [0,100,300,700,700],
    "plan_weight": [0,1,2,3,4],
    "products": [
        {
            "name": "Gaming GPT",
            "features": [
                {"name": "Tokens", "values": ["10 one off","100 /month", "300 /month", "700 /month", "700 /month"]},
                {"name": "Rate Limit", "values": ["1 Question Every 5 Minutes","1 Question Every 2 Minutes", "1 Question every 1 Minute", "1 Question every 30 Seconds", "1 Question every 10 Seconds"]},
            ]
        },
        {
            "name": "Insights API",
            "features": [
                {"name": "Historical Data Access", "values": ["None","1 month", "6 months", "12 months", "24 months"]},
                {"name": "Tech Support", "values": ["None","Basic", "Basic", "Priority", "Dedicated"]},
                {"name": "API Keys", "values": ["0 Seats","1 Seat", "2 Seats", "5 Seats", "10 Seats"]},
                {"name": "General Ranking", "values": ["—","✓", "✓", "✓", "✓"]},
                {"name": "Aggregated Rankings", "values": ["—","✓", "✓", "✓", "✓"]},
                {"name": "Ranking Genres", "values": ["—","✓", "✓", "✓", "✓"]},
                {"name": "Ranking List Types", "values": ["—","✓", "✓", "✓", "✓"]},
                {"name": "Single App Details", "values": ["—","—", "✓", "✓", "✓"]},
                {"name": "Details All Apps", "values": ["—","—", "✓", "✓", "✓"]},
                {"name": "All Publishers", "values": ["—","—", "✓", "✓", "✓"]},
                {"name": "App Availability", "values": ["—","—", "—", "✓", "✓"]},
                {"name": "App Estimates Downloads", "values": ["—","—", "—", "✓", "✓"]},
                {"name": "App Estimates Revenue", "values": ["—","—", "—", "✓", "✓"]},
                {"name": "Chrome Store Extensions", "values": ["—","—", "—", "✓", "✓"]},
                {"name": "Apple App Privacy", "values": ["—","—", "—", "✓", "✓"]},
                {"name": "Google Data Safety", "values": ["—","—", "—", "✓", "✓"]},
                {"name": "Reviews All Apps", "values": ["—","—", "—", "—", "✓"]},
                {"name": "App Ads", "values": ["—","—", "—", "—", "✓"]}
            ]
        },
        {
            "name": "Data Marketplace",
            "features": [
                {"name": "Historical Data Access", "values": ["None","1 month", "6 months", "12 months", "24 months"]},
                {"name": "Tech Support", "values": ["None","Basic", "Basic", "Priority", "Dedicated"]},
                {"name": "API Keys", "values": ["0 Seats","1 Seat", "2 Seats", "5 Seats", "10 Seats"]},
                {"name": "General Ranking", "values": ["—","✓", "✓", "✓", "✓"]},
                {"name": "Aggregated Rankings", "values": ["—","✓", "✓", "✓", "✓"]},
                {"name": "Ranking Genres", "values": ["—","✓", "✓", "✓", "✓"]},
                {"name": "Ranking List Types", "values": ["—","✓", "✓", "✓", "✓"]},
                {"name": "Single App Details", "values": ["—","—", "✓", "✓", "✓"]},
                {"name": "Details All Apps", "values": ["—","—", "✓", "✓", "✓"]},
                {"name": "All Publishers", "values": ["—","—", "✓", "✓", "✓"]},
                {"name": "App Availability", "values": ["—","—", "—", "✓", "✓"]},
                {"name": "App Estimates Downloads", "values": ["—","—", "—", "✓", "✓"]},
                {"name": "App Estimates Revenue", "values": ["—","—", "—", "✓", "✓"]},
                {"name": "Chrome Store Extensions", "values": ["—","—", "—", "✓", "✓"]},
                {"name": "Apple App Privacy", "values": ["—","—", "—", "✓", "✓"]},
                {"name": "Google Data Safety", "values": ["—","—", "—", "✓", "✓"]},
                {"name": "Reviews All Apps", "values": ["—","—", "—", "—", "✓"]},
                {"name": "App Ads", "values": ["—","—", "—", "—", "✓"]}
            ]
        }
    ]
}

COIN_BUNDLES = [
    {"coins": 10, "price_in_cents": 2000, "label": "10 for $20"},
    {"coins": 20, "price_in_cents": 4000, "label": "20 for $40"},
    {"coins": 50, "price_in_cents": 10000, "label": "50 for $100"},
    {"coins": 100, "price_in_cents": 20000, "label": "100 for $200"},
]

# Ignite api key
IGNITE_API_KEY = os.getenv("IGNITE_API_KEY", "test")

# Rate limiting.
RATELIMIT_STORAGE_URL = REDIS_URL
RATELIMIT_STRATEGY = "fixed-window-elastic-expiry"
RATELIMIT_HEADERS_ENABLED = True

# Google Analytics.
ANALYTICS_GOOGLE_UA = os.getenv("ANALYTICS_GOOGLE_UA", None)

# http basic auth
BASIC_AUTH_CREDS = os.getenv("USERS",None)