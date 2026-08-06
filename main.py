import logging
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, Request, Response, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from database import init_db, get_db
from models import Tenant, ChatHistory
from schemas import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    WhatsAppWebhookPayload
)
from ai_service import generate_ai_response
from whatsapp_client import send_whatsapp_message, notify_human_agent

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn.error")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler to initialize database tables on startup."""
    logger.info("Starting up WhatsApp AI Chatbot service...")
    await init_db()
    yield
    logger.info("Shutting down WhatsApp AI Chatbot service...")

app = FastAPI(
    title="Multi-Tenant WhatsApp AI Chatbot API",
    description="Production-ready multi-tenant Python FastAPI backend with SQLite, OpenAI gpt-4o-mini, and Meta WhatsApp Cloud API.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "online",
        "service": "Multi-Tenant WhatsApp AI Chatbot Backend",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Tenant))
        tenants_count = len(result.scalars().all())
        return {
            "status": "healthy",
            "database": "connected",
            "tenants_count": tenants_count
        }
    except Exception as e:
        logger.error(f"Health check database error: {e}")
        return {"status": "unhealthy", "database_error": str(e)}


# ---------------------------------------------------------------------------
# META WHATSAPP WEBHOOK ENDPOINTS
# ---------------------------------------------------------------------------

@app.get("/webhook", tags=["WhatsApp Webhook"])
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge")
):
    """
    Meta Webhook Verification Endpoint.
    Meta sends a GET request to verify the webhook endpoint URL during setup.
    """
    logger.info(f"Received webhook verification request: mode={hub_mode}, token={hub_verify_token}")

    if hub_mode == "subscribe" and hub_verify_token == settings.META_VERIFY_TOKEN:
        logger.info("Webhook verification successful!")
        # Meta expects the challenge returned as a plain text string / integer response
        return Response(content=hub_challenge, media_type="text/plain", status_code=200)

    logger.warning("Webhook verification failed: Invalid verify token or mode mismatch.")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Verification token mismatch"
    )


@app.post("/webhook", tags=["WhatsApp Webhook"])
async def process_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Receives incoming WhatsApp events from Meta Graph API.
    Resolves tenant via phone_number_id, processes message with OpenAI gpt-4o-mini,
    and sends response back via Meta Graph API.
    """
    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse incoming webhook JSON: {e}")
        return Response(content="EVENT_RECEIVED", status_code=200)

    logger.info(f"Incoming Webhook Payload: {body}")

    # Extract entry data
    entries = body.get("entry", [])
    if not entries:
        return Response(content="EVENT_RECEIVED", status_code=200)

    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})
            metadata = value.get("metadata", {})
            phone_number_id = metadata.get("phone_number_id")

            messages = value.get("messages", [])
            if not messages or not phone_number_id:
                continue

            for message in messages:
                # Process text messages
                msg_type = message.get("type")
                if msg_type != "text":
                    logger.info(f"Skipping non-text message type: {msg_type}")
                    continue

                customer_phone = message.get("from")
                user_text = message.get("text", {}).get("body", "").strip()

                if not customer_phone or not user_text:
                    continue

                logger.info(
                    f"Message received on Phone Number ID '{phone_number_id}' "
                    f"from '{customer_phone}': '{user_text}'"
                )

                # -----------------------------------------------------------
                # TENANT RESOLVER
                # -----------------------------------------------------------
                stmt = select(Tenant).where(Tenant.whatsapp_phone_number_id == phone_number_id)
                result = await db.execute(stmt)
                tenant = result.scalar_one_or_none()

                if not tenant:
                    logger.error(f"No tenant found matching whatsapp_phone_number_id='{phone_number_id}'")
                    continue

                logger.info(f"Resolved tenant: ID={tenant.id}, Business='{tenant.business_name}'")

                # Fetch past chat history for context (up to 10 previous turns)
                history_stmt = (
                    select(ChatHistory)
                    .where(
                        ChatHistory.tenant_id == tenant.id,
                        ChatHistory.customer_phone_number == customer_phone
                    )
                    .order_by(ChatHistory.created_at.asc())
                )
                history_res = await db.execute(history_stmt)
                history_records = history_res.scalars().all()

                formatted_history = [
                    {"role": item.role, "content": item.content} for item in history_records
                ]

                # Generate Multilingual AI Response (gpt-4o-mini)
                ai_reply, is_handoff_requested = await generate_ai_response(
                    system_prompt=tenant.system_prompt,
                    knowledge_base=tenant.knowledge_base,
                    chat_history=formatted_history,
                    user_message=user_text
                )

                # Store user message & AI response in database
                user_history = ChatHistory(
                    tenant_id=tenant.id,
                    customer_phone_number=customer_phone,
                    role="user",
                    content=user_text
                )
                ai_history = ChatHistory(
                    tenant_id=tenant.id,
                    customer_phone_number=customer_phone,
                    role="assistant",
                    content=ai_reply
                )
                db.add(user_history)
                db.add(ai_history)
                await db.commit()

                # Send AI response back to customer via Meta Cloud API
                await send_whatsapp_message(
                    phone_number_id=tenant.whatsapp_phone_number_id,
                    recipient_phone=customer_phone,
                    message_text=ai_reply,
                    meta_access_token=tenant.meta_access_token
                )

                # Handle Human Handoff if requested
                if is_handoff_requested and tenant.human_handoff_number:
                    logger.info(f"Triggering human handoff notification to {tenant.human_handoff_number}")
                    await notify_human_agent(
                        phone_number_id=tenant.whatsapp_phone_number_id,
                        handoff_number=tenant.human_handoff_number,
                        customer_phone=customer_phone,
                        last_user_message=user_text,
                        meta_access_token=tenant.meta_access_token
                    )

    # Meta requires a 200 OK HTTP response to acknowledge receipt of event
    return Response(content="EVENT_RECEIVED", status_code=200)


# ---------------------------------------------------------------------------
# TENANT MANAGEMENT CRUD ENDPOINTS
# ---------------------------------------------------------------------------

@app.post("/api/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED, tags=["Tenant Admin"])
async def create_tenant(tenant_in: TenantCreate, db: AsyncSession = Depends(get_db)):
    """Create a new business tenant."""
    # Check if phone number ID already exists
    stmt = select(Tenant).where(Tenant.whatsapp_phone_number_id == tenant_in.whatsapp_phone_number_id)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant with whatsapp_phone_number_id='{tenant_in.whatsapp_phone_number_id}' already exists."
        )

    new_tenant = Tenant(**tenant_in.model_dump())
    db.add(new_tenant)
    await db.commit()
    await db.refresh(new_tenant)
    logger.info(f"Created new tenant: {new_tenant.business_name} (ID: {new_tenant.id})")
    return new_tenant


@app.get("/api/tenants", response_model=List[TenantResponse], tags=["Tenant Admin"])
async def list_tenants(db: AsyncSession = Depends(get_db)):
    """List all registered tenants."""
    stmt = select(Tenant).order_by(Tenant.id.asc())
    result = await db.execute(stmt)
    return result.scalars().all()


@app.get("/api/tenants/{tenant_id}", response_model=TenantResponse, tags=["Tenant Admin"])
async def get_tenant(tenant_id: int, db: AsyncSession = Depends(get_db)):
    """Get tenant details by ID."""
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    tenant = (await db.execute(stmt)).scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@app.put("/api/tenants/{tenant_id}", response_model=TenantResponse, tags=["Tenant Admin"])
async def update_tenant(tenant_id: int, tenant_update: TenantUpdate, db: AsyncSession = Depends(get_db)):
    """Update tenant prompt, knowledge base, or Meta credentials."""
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    tenant = (await db.execute(stmt)).scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    update_data = tenant_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tenant, field, value)

    await db.commit()
    await db.refresh(tenant)
    return tenant


@app.delete("/api/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tenant Admin"])
async def delete_tenant(tenant_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a tenant by ID."""
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    tenant = (await db.execute(stmt)).scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    await db.delete(tenant)
    await db.commit()
    return None
