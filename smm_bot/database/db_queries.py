import aiosqlite
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)
DB_PATH = "smm_bot.db"


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cursor.fetchone()


async def create_or_update_user(user_id: int, username, full_name: str, referrer_id=None) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        existing = await cursor.fetchone()
        if existing:
            await db.execute(
                "UPDATE users SET username=?, full_name=?, last_active=datetime('now') WHERE user_id=?",
                (username, full_name, user_id),
            )
            await db.commit()
            return False
        else:
            await db.execute(
                "INSERT INTO users (user_id, username, full_name, referrer_id) VALUES (?, ?, ?, ?)",
                (user_id, username, full_name, referrer_id),
            )
            await db.commit()
            return True


async def update_user_balance(user_id: int, amount: float, add: bool = True):
    op = "+" if add else "-"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE users SET balance = balance {op} ? WHERE user_id = ?",
            (abs(amount), user_id),
        )
        await db.commit()


async def update_total_spent(user_id: int, amount: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET total_spent = total_spent + ? WHERE user_id = ?",
            (amount, user_id),
        )
        await db.commit()


async def set_user_balance(user_id: int, amount: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = ? WHERE user_id = ?", (amount, user_id))
        await db.commit()


async def ban_user(user_id: int, ban: bool = True):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_banned = ? WHERE user_id = ?", (1 if ban else 0, user_id)
        )
        await db.commit()


async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE is_banned = 0")
        return await cursor.fetchall()


async def get_user_count() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        total = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        active = (await (await db.execute(
            "SELECT COUNT(*) FROM users WHERE last_active >= datetime('now', '-7 days')"
        )).fetchone())[0]
        banned = (await (await db.execute(
            "SELECT COUNT(*) FROM users WHERE is_banned = 1"
        )).fetchone())[0]
        return {"total": total, "active": active, "banned": banned}


async def get_referral_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0


async def create_order(user_id, service_id, service_name, link, quantity, charge, api_order_id=None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO orders (user_id, api_order_id, service_id, service_name, link, quantity, charge) VALUES (?,?,?,?,?,?,?)",
            (user_id, api_order_id, service_id, service_name, link, quantity, charge),
        )
        await db.commit()
        return cursor.lastrowid


async def get_user_orders(user_id: int, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        return await cursor.fetchall()


async def get_order_by_id(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        return await cursor.fetchone()


async def update_order_status(order_id: int, status: str, api_order_id: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if api_order_id:
            await db.execute(
                "UPDATE orders SET status=?, api_order_id=?, updated_at=datetime('now') WHERE id=?",
                (status, api_order_id, order_id),
            )
        else:
            await db.execute(
                "UPDATE orders SET status=?, updated_at=datetime('now') WHERE id=?",
                (status, order_id),
            )
        await db.commit()


async def get_all_orders(status: str = None, limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cursor = await db.execute(
                "SELECT * FROM orders WHERE status=? ORDER BY created_at DESC LIMIT ?", (status, limit)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?", (limit,)
            )
        return await cursor.fetchall()


async def log_transaction(user_id: int, amount: float, ttype: str, description: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO transactions (user_id, amount, type, description) VALUES (?,?,?,?)",
            (user_id, amount, ttype, description),
        )
        await db.commit()


async def get_total_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        total_balance = (await (await db.execute("SELECT COALESCE(SUM(balance),0) FROM users")).fetchone())[0]
        total_spent = (await (await db.execute("SELECT COALESCE(SUM(total_spent),0) FROM users")).fetchone())[0]
        total_orders = (await (await db.execute("SELECT COUNT(*) FROM orders")).fetchone())[0]
        return {"total_balance": total_balance, "total_spent": total_spent, "total_orders": total_orders}


async def create_promo(code: str, amount: float, max_uses: int = 1) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO promo_codes (code, amount, max_uses) VALUES (?, ?, ?)", (code, amount, max_uses)
            )
            await db.commit()
            return True
    except aiosqlite.IntegrityError:
        return False


async def get_promo(code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM promo_codes WHERE code=? AND is_active=1", (code,)
        )
        return await cursor.fetchone()


async def redeem_promo(user_id: int, promo_id: int) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO promo_usage (user_id, promo_id) VALUES (?, ?)", (user_id, promo_id)
            )
            await db.execute(
                "UPDATE promo_codes SET used_count = used_count + 1 WHERE id = ?", (promo_id,)
            )
            await db.execute(
                "UPDATE promo_codes SET is_active = 0 WHERE id = ? AND used_count >= max_uses", (promo_id,)
            )
            await db.commit()
            return True
    except aiosqlite.IntegrityError:
        return False


async def has_user_used_promo(user_id: int, promo_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM promo_usage WHERE user_id=? AND promo_id=?", (user_id, promo_id)
        )
        return await cursor.fetchone() is not None


async def get_all_promos():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM promo_codes ORDER BY created_at DESC")
        return await cursor.fetchall()


async def delete_promo(promo_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM promo_codes WHERE id = ?", (promo_id,))
        await db.commit()


async def can_claim_daily_bonus(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM daily_bonus_log WHERE user_id=? AND claimed_at >= datetime('now', '-24 hours')",
            (user_id,),
        )
        return await cursor.fetchone() is None


async def log_daily_bonus(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO daily_bonus_log (user_id) VALUES (?)", (user_id,))
        await db.commit()


async def create_support_ticket(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE support_tickets SET status='closed' WHERE user_id=? AND status='open'", (user_id,)
        )
        cursor = await db.execute("INSERT INTO support_tickets (user_id) VALUES (?)", (user_id,))
        await db.commit()
        return cursor.lastrowid


async def get_open_ticket(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM support_tickets WHERE user_id=? AND status='open'", (user_id,)
        )
        return await cursor.fetchone()


async def get_ticket_by_id(ticket_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM support_tickets WHERE id = ?", (ticket_id,))
        return await cursor.fetchone()


async def close_ticket(ticket_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE support_tickets SET status='closed', updated_at=datetime('now') WHERE id=?", (ticket_id,)
        )
        await db.commit()


async def log_support_message(ticket_id, sender_id, is_admin, message=None, media_id=None, media_type=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO support_messages (ticket_id, sender_id, is_admin, message, media_id, media_type) VALUES (?,?,?,?,?,?)",
            (ticket_id, sender_id, 1 if is_admin else 0, message, media_id, media_type),
        )
        await db.commit()


async def get_all_open_tickets():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT st.*, u.username, u.full_name FROM support_tickets st
               JOIN users u ON st.user_id = u.user_id
               WHERE st.status = 'open' ORDER BY st.updated_at DESC"""
        )
        return await cursor.fetchall()


async def get_setting(key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT value FROM bot_settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row[0] if row else None


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)", (key, value)
        )
        await db.commit()

        # Barcha foydalanuvchilarni olish (Broadcast uchun)
async def get_all_users():
    # Sizning bazangizga qarab moslang (masalan: PostgreSQL yoki SQLite)
    # return await db.fetch_all("SELECT user_id FROM users")
    pass

# Statistikani olish
async def get_stats():
    # Masalan:
    # total_users = await db.fetch_val("SELECT COUNT(*) FROM users")
    # total_balance = await db.fetch_val("SELECT COALESCE(SUM(balance), 0) FROM users")
    # total_spent = await db.fetch_val("SELECT COALESCE(SUM(total_spent), 0) FROM users")
    # return {"total_users": total_users, "total_balance": total_balance, "total_spent": total_spent, "active_today": 0}
    return {"total_users": 0, "total_balance": 0, "total_spent": 0, "active_today": 0, "total_orders": 0}

# Promo kod qo'shish
async def add_promo_code(code: str, amount: int, max_uses: int):
    # Masalan:
    # await db.execute("INSERT INTO promos (code, amount, max_uses, used_count, is_active) VALUES (:code, :amount, :max_uses, 0, True)", {"code": code, "amount": amount, "max_uses": max_uses})
    pass