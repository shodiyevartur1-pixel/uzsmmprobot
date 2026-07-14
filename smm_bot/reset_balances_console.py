import asyncio
import aiosqlite

DB_PATH = "smm_bot.db"


async def main():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute("SELECT user_id, balance FROM users")
        users = await cursor.fetchall()

        # Balansi bor foydalanuvchilar uchun tranzaksiya tarixiga yozib qo'yamiz
        for u in users:
            old_balance = u["balance"] or 0
            if old_balance:
                await db.execute(
                    "INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)",
                    (u["user_id"], old_balance, "admin_reset", "Konsoldan: balans 0 qilindi"),
                )

        await db.execute("UPDATE users SET balance = 0")
        await db.commit()

        print(f"✅ Jami {len(users)} ta foydalanuvchi balansi 0 ga tushirildi.")


if __name__ == "__main__":
    asyncio.run(main())
