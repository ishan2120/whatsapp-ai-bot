import asyncio
import logging
from database import AsyncSessionLocal
from models import Tenant
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("update_token")

TOKEN = "EAAjfYY4wqiYBSORE4QYSFD9QGUt1QTMRn4ZCRWfmxXyOMnG1Baixqobu5szEbWG7554T88KqsSyV6oifZABeZCfJE8HRPZCUXrQ7SRKXgZCHp2r3qYgOZB9TZAHovFd39ZBKTL3EkNqCNaiWl9qdEWtXp3JT59oL9bJ4bRm0ZBSIE1qPTbHZCa4WQVSAFJR9bnhdZBQbfIll6glfYTq3aRbXrYIUeEk9tF27ou9zgEYbW7Xk4recf8gZBQzq1JDsDsr1zsSqouSibaimJWS66w4B3XFZBcPDT4wZDZD"
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
        logger.info(f"SUCCESS: Meta Access Token updated for tenant '{tenant.business_name}' (ID: {tenant.id})!")

if __name__ == "__main__":
    asyncio.run(update_token())
