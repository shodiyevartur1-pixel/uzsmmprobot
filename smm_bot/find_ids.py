import aiohttp
import asyncio
import json

API_URL = "https://peakerr.com/api/v2"
API_KEY = "bc2e73e6cd57dd82150866e2480c9a4d"

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, data={"key": API_KEY, "action": "services"}) as resp:
            raw = await resp.json(content_type=None)

    # List ekanligini tekshirish
    if isinstance(raw, list):
        services = raw
    elif isinstance(raw, dict):
        services = list(raw.values())
    else:
        print("❌ Noto'g'ri format:", type(raw))
        return

    # Faqat dict bo'lgan elementlarni olish
    services = [s for s in services if isinstance(s, dict)]
    print(f"✅ Jami {len(services)} ta xizmat topildi\n")

    keywords = {
        "TG A'ZOLAR":      ["telegram member"],
        "TG KO'RISHLAR":   ["telegram view"],
        "TG REAKTSIYA":    ["telegram reaction"],
        "TG IZOH":         ["telegram comment"],
        "IG OBUNACHILAR":  ["instagram follower"],
        "IG LAYKLAR":      ["instagram like"],
        "IG KO'RISHLAR":   ["instagram view", "instagram reel"],
        "YT KO'RISHLAR":   ["youtube view"],
        "YT OBUNACHILAR":  ["youtube subscriber"],
        "YT LAYKLAR":      ["youtube like"],
        "TT OBUNACHILAR":  ["tiktok follower"],
        "TT LAYKLAR":      ["tiktok like"],
        "TT KO'RISHLAR":   ["tiktok view"],
    }

    for label, keys in keywords.items():
        matched = [
            s for s in services
            if any(k in s.get("name", "").lower() for k in keys)
        ][:6]

        print(f"\n{'='*65}")
        print(f"  {label}")
        print(f"{'='*65}")
        if matched:
            for s in matched:
                print(f"  ID: {str(s['service']):<8} | ${s['rate']}/1000 | min:{s['min']} | {s['name'][:48]}")
        else:
            print("  Topilmadi")

    with open("filtered_services.json", "w", encoding="utf-8") as f:
        json.dump(
            {label: [s for s in services if any(k in s.get("name","").lower() for k in keys)][:6]
             for label, keys in keywords.items()},
            f, ensure_ascii=False, indent=2
        )
    print("\n✅ filtered_services.json ga saqlandi!")

if __name__ == "__main__":
    asyncio.run(main())