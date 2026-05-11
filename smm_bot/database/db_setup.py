import aiosqlite
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path("smm_bot.db")


async def get_db():
    """Get a database connection."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    """Initialize all database tables."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        await db.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;

            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                full_name   TEXT NOT NULL,
                balance     REAL NOT NULL DEFAULT 0.0,
                total_spent REAL NOT NULL DEFAULT 0.0,
                referrer_id INTEGER REFERENCES users(user_id),
                is_banned   INTEGER NOT NULL DEFAULT 0,
                is_admin    INTEGER NOT NULL DEFAULT 0,
                joined_at   TEXT NOT NULL DEFAULT (datetime('now')),
                last_active TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS orders (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL REFERENCES users(user_id),
                api_order_id  TEXT,
                service_id    TEXT NOT NULL,
                service_name  TEXT NOT NULL,
                link          TEXT NOT NULL,
                quantity      INTEGER NOT NULL,
                charge        REAL NOT NULL,
                status        TEXT NOT NULL DEFAULT 'pending',
                created_at    TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS promo_codes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                code        TEXT NOT NULL UNIQUE,
                amount      REAL NOT NULL,
                max_uses    INTEGER NOT NULL DEFAULT 1,
                used_count  INTEGER NOT NULL DEFAULT 0,
                is_active   INTEGER NOT NULL DEFAULT 1,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS promo_usage (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL REFERENCES users(user_id),
                promo_id   INTEGER NOT NULL REFERENCES promo_codes(id),
                used_at    TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(user_id, promo_id)
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(user_id),
                amount      REAL NOT NULL,
                type        TEXT NOT NULL,
                description TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS daily_bonus_log (
                user_id    INTEGER NOT NULL REFERENCES users(user_id),
                claimed_at TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (user_id, claimed_at)
            );

            CREATE TABLE IF NOT EXISTS support_tickets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(user_id),
                status      TEXT NOT NULL DEFAULT 'open',
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS support_messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id   INTEGER NOT NULL REFERENCES support_tickets(id),
                sender_id   INTEGER NOT NULL,
                is_admin    INTEGER NOT NULL DEFAULT 0,
                message     TEXT,
                media_id    TEXT,
                media_type  TEXT,
                sent_at     TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS number_sessions (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL REFERENCES users(user_id),
                activation_id TEXT NOT NULL,
                phone_number  TEXT NOT NULL,
                country       TEXT NOT NULL,
                service       TEXT NOT NULL,
                status        TEXT NOT NULL DEFAULT 'waiting',
                created_at    TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS bot_settings (
                key     TEXT PRIMARY KEY,
                value   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS broadcasts (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id      INTEGER NOT NULL,
                message_text  TEXT,
                media_id      TEXT,
                media_type    TEXT,
                total_sent    INTEGER DEFAULT 0,
                total_failed  INTEGER DEFAULT 0,
                created_at    TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
            CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
            CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
            CREATE INDEX IF NOT EXISTS idx_support_tickets_user_id ON support_tickets(user_id);
            CREATE INDEX IF NOT EXISTS idx_users_referrer ON users(referrer_id);
        """)
        await db.commit()
        logger.info("✅ Database initialized successfully.")
    finally:
        await db.close()