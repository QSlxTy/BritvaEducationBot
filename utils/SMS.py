import aiohttp

from src.config import Configuration


async def send_sms(phone):
    url = "https://zvonok.com/manager/cabapi_external/api/v1/phones/tellcode/"
    params = {
        "public_key": str(Configuration.phone_token),
        "phone": str(phone),
        "campaign_id": 21052774,
        "json": 1
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            return await response.json()
