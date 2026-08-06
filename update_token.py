import asyncio
import logging
from database import AsyncSessionLocal
from models import Tenant
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("update_token")

TOKEN = "EAAjfYY4wqiYBSFUDPvPZAcBBEdDXNI8bEAlvLqMGsALEtFAVKniNFPLU5jdOodS53bYOyOettApsQQIxflC0Ca4ywHRayUnbZBtnHfxiKJ5DJdEg5ZBsafyZBLrbw4byqJPhqJdAwPiCQiX2HqCAZCSUekdKcrqz2yiAzPPCNV3JECNZBXVNmZBx9CxsxSSxY54PZCGQStST56bFbEgggTCRFDkh5HWg8MbO5ECctF2SPeVpSZAXETkg3e2p608BdizzYKkWnREDXAoPTydVgJWNWZCIQG"
PHONE_ID = "1157440684128924"

async def update_token():
    async with AsyncSessionLocal() as session:
        stmt = select(Tenant).where(Tenant.whatsapp_phone_number_id == PHONE_ID)
        tenant = (await session.execute(stmt)).scalar_one_or_none()

        if not tenant:
            logger.error(f"Tenant with phone_number_id='{PHONE_ID}' not found.")
            return

        tenant.meta_access_token = TOKEN
        await session.commit()
        logger.info(f"SUCCESS: Permanent Meta Access Token updated for tenant '{tenant.business_name}' (ID: {tenant.id})!")

if __name__ == "__main__":
    asyncio.run(update_token())
