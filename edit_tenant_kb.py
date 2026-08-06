import asyncio
import logging
import httpx
from database import AsyncSessionLocal, init_db
from models import Tenant
from sqlalchemy import select

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("edit_kb")

# ==============================================================================
# EDIT YOUR HOTEL PACKAGES & PRICES HERE:
# ==============================================================================
NEW_KNOWLEDGE_BASE = """=== WASALA NATURE RESORT - BANQUET & EVENTS MASTER KNOWLEDGE BASE ===

🏛️ BANQUET HALLS & SEATING CAPACITY:
1. Grand Royal Ballroom:
   - Capacity: Up to 650 guests (Banquet setup) | 800 guests (Theater setup)
   - Features: Centralized AC, Crystal Chandeliers, Full Stage, Private Bridal Suite.

2. Lotus Pavilion (Outdoor Lakefront Venue):
   - Capacity: Up to 350 guests
   - Features: Open-air lakefront view, garden illumination, wooden porch stage.

🍽️ WEDDING & BANQUET PACKAGES (Per Head Pricing):
- Gold Buffet Package: LKR 5,500 net per head
  (Includes: Welcome Drink, 2 Salads, 2 Rice items, Chicken/Fish/Pork, 3 Veg, 3 Desserts, Complementary Bridal Room)

- Platinum Luxury Package: LKR 7,500 net per head
  (Includes: International Seafood & Meat Buffet, Welcome Mocktails, Live Action Stations, Honeymoon Suite)

- Silver Budget Package: LKR 4,200 net per head
  (Includes: Welcome Drink, Fried Rice, Chicken Curry, Dhal, Salad, Ice Cream)

- Corporate Conference Package: LKR 3,800 net per head
  (Includes: Morning Tea & Snacks, Buffet Lunch, Afternoon Tea, Projector, Sound System)

📄 OFFICIAL BROCHURES & DOCUMENTS:
- 2026 Wedding Packages Brochure PDF: https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf

📋 POLICIES & DEPOSIT:
- Advance Booking Deposit: 25% to hold date, balance due 7 days prior to event.
- Corkage Fee: Free corkage for hard liquor if soft drinks purchased from hotel.
- Music Cut-off Time: 11:30 PM.
"""

CLOUD_RENDER_URL = "https://whatsapp-ai-bot-3f6n.onrender.com/api/tenants/1"

async def update_knowledge_base():
    """Updates local SQLite database and live Render cloud API."""
    await init_db()

    # 1. Update Local Database
    async with AsyncSessionLocal() as session:
        stmt = select(Tenant).where(Tenant.id == 1)
        tenant = (await session.execute(stmt)).scalar_one_or_none()
        if not tenant:
            stmt = select(Tenant).where(Tenant.whatsapp_phone_number_id == "1157440684128924")
            tenant = (await session.execute(stmt)).scalar_one_or_none()

        if tenant:
            tenant.knowledge_base = NEW_KNOWLEDGE_BASE
            await session.commit()
            logger.info(f"✅ Local Database updated for tenant '{tenant.business_name}' (ID: {tenant.id})")

    # 2. Update Render Cloud API
    async with httpx.AsyncClient() as client:
        try:
            payload = {"knowledge_base": NEW_KNOWLEDGE_BASE}
            res = await client.put(CLOUD_RENDER_URL, json=payload, timeout=30.0)
            if res.status_code == 200:
                logger.info("🚀 LIVE RENDER CLOUD SERVER UPDATED SUCCESSFULLY!")
            else:
                logger.warning(f"Render API response status: {res.status_code}")
        except Exception as e:
            logger.error(f"Could not connect to Render API: {e}")

if __name__ == "__main__":
    asyncio.run(update_knowledge_base())
