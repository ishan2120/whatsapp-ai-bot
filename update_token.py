import asyncio
import logging
from database import AsyncSessionLocal
from models import Tenant
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("update_token")

TOKEN = "EAAjfYY4wqiYBSThnYrP7631PGyrcuBgrNoQvITTe1HtEJRIr8C8D2ZBQFOw59hdVhyiFoqd45ANOHgPhk4D7I3j95bAWmor5JNJgvqZB2Evny4zd1K5uC6yOGvSynoAj1t7n43ZCA2BLI8NqwXFXMSs0ney9IbncFkaopKBVXOyCGBE2w8luVzYbswCwJOYozXBcT5vVaO1nJN6qzdvIzmKF2BcIfsz1D7OgBEMmwxuj5vYEfkyUqXlVYAG7k6JprgO7VjUHLelLLpAuRls9p2HpAZDZD"
PHONE_ID = "1157440684128924"

async def update_token():
    async with AsyncSessionLocal() as session:
        stmt = select(Tenant).where(Tenant.whatsapp_phone_number_id == PHONE_ID)
        tenants = (await session.execute(stmt)).scalars().all()

        for tenant in tenants:
            tenant.meta_access_token = TOKEN
            logger.info(f"SUCCESS: Active Meta Access Token updated for tenant '{tenant.business_name}' (ID: {tenant.id})!")
        await session.commit()

if __name__ == "__main__":
    asyncio.run(update_token())
