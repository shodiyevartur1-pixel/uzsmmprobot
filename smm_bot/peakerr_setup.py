import aiohttp
import asyncio
import json

API_URL = "https://peakerr.com/api/v2"
API_KEY = "bc2e73e6cd57dd82150866e2480c9a4d"


async def main():
    async with aiohttp.ClientSession() as session:

        # 1. Balans tekshirish
        print("🔍 Peakerr ulanishini tekshirmoqda...")
        async with session.post(API_URL, data={"key": API_KEY, "action": "balance"}) as resp:
            result = await resp.json()
            if "balance" in result:
                print(f"✅ Ulanish muvaffaqiyatli!")
                print(f"💰 Balans: ${result['balance']}\n")
            else:
                print(f"❌ Xato: {result}")
                return

        # 2. Barcha xizmatlarni olish
        print("📋 Xizmatlar yuklanmoqda...")
        async with session.post(API_URL, data={"key": API_KEY, "action": "services"}) as resp:
            services = await resp.json()

        # 3. Telegram
        print("\n🔵 TELEGRAM xizmatlari:")
        print("-" * 70)
        tg = [s for s in services if "telegram" in s.get("name", "").lower()
              or "telegram" in s.get("category", "").lower()]
        for s in tg[:30]:
            print(f"  ID: {str(s['service']):<8} | ${s['rate']}/1000 | min:{s['min']} | {s['name'][:45]}")

        # 4. Instagram
        print("\n🟣 INSTAGRAM xizmatlari:")
        print("-" * 70)
        ig = [s for s in services if "instagram" in s.get("name", "").lower()
              or "instagram" in s.get("category", "").lower()]
        for s in ig[:20]:
            print(f"  ID: {str(s['service']):<8} | ${s['rate']}/1000 | min:{s['min']} | {s['name'][:45]}")

        # 5. YouTube
        print("\n🔴 YOUTUBE xizmatlari:")
        print("-" * 70)
        yt = [s for s in services if "youtube" in s.get("name", "").lower()
              or "youtube" in s.get("category", "").lower()]
        for s in yt[:15]:
            print(f"  ID: {str(s['service']):<8} | ${s['rate']}/1000 | min:{s['min']} | {s['name'][:45]}")

        # 6. TikTok
        print("\n⚫ TIKTOK xizmatlari:")
        print("-" * 70)
        tt = [s for s in services if "tiktok" in s.get("name", "").lower()
              or "tiktok" in s.get("category", "").lower()]
        for s in tt[:15]:
            print(f"  ID: {str(s['service']):<8} | ${s['rate']}/1000 | min:{s['min']} | {s['name'][:45]}")

        # 7. JSON ga saqlash
        with open("peakerr_services.json", "w", encoding="utf-8") as f:
            json.dump(services, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Barcha xizmatlar 'peakerr_services.json' ga saqlandi!")
        print(f"📦 Jami: {len(services)} ta xizmat")
        print("\n💡 Endi peakerr_services.json faylini ochib kerakli ID larni oling")
        print("   va orders.py dagi 'service' maydonlarini yangilang.")


if __name__ == "__main__":
    asyncio.run(main())
