import asyncio
import logging
from database import AsyncSessionLocal
from models import Tenant
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("update_token")

TOKEN = "EAAjfYY4wqiYBSOuuWKVaD4zuCG9qZBMZCLw89LeAwyZAqf81yEzuVitCQjWIeIP2bIVZBRPZAwp5eFnnLsTDDbgVAraB199PxB6rrWFXaAqRblCT9eKSHSf1bHktr4lEYjJwsFQrezxH5kFzUQ6B49yPl3oXlppDcn2Pg4pbZBNzXXvrX9aIdRMBhXAZATkqd37KkZCeZArj53kyHolBTwoZAhu99ZAkGOS8Mon0D444z31yBtaqr2mEC48hZCxIRJ4ZCMB1XSYWZAYuUIH3WvTamZAUSEmt5AZA"
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
        logger.info(f"SUCCESS: Active Meta Access Token updated for tenant '{tenant.business_name}' (ID: {tenant.id})!")

if __name__ == "__main__":
    asyncio.run(update_token())
