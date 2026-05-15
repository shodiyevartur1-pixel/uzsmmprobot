import aiohttp
from config import settings

async def smm_request(data: dict) -> dict:
    payload = {"key": settings.SMM_API_KEY, **data}
    async with aiohttp.ClientSession() as session:
        async with session.post(settings.SMM_API_URL, data=payload) as resp:
            return await resp.json()

async def get_balance() -> float:
    result = await smm_request({"action": "balance"})
    return float(result.get("balance", 0))

async def create_order(service_id: int, link: str, quantity: int) -> dict:
    return await smm_request({
        "action": "add",
        "service": service_id,
        "link": link,
        "quantity": quantity,
    })

async def get_order_status(order_id: int) -> dict:
    return await smm_request({
        "action": "status",
        "order": order_id,
    })

async def get_services() -> list:
    return await smm_request({"action": "services"})