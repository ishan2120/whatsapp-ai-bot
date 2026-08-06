from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

# Tenant Schemas
class TenantBase(BaseModel):
    business_name: str = Field(..., example="Kandy Spice Restaurant")
    whatsapp_phone_number_id: str = Field(..., example="109876543210987")
    meta_access_token: str = Field(..., example="EAAXXXXXX...")
    system_prompt: str = Field(
        default="You are a helpful customer support assistant for Kandy Spice Restaurant. Respond politely in the language the customer uses (English, Sinhala, or Singlish).",
        example="You are a friendly customer service AI for Kandy Spice."
    )
    knowledge_base: str = Field(
        default="Hours: 8 AM - 10 PM. Delivery available in Kandy city. Specials: Rice and Curry (Rs. 800), Kottu (Rs. 950).",
        example="Menu: Rice & Curry Rs 800. Location: Main St, Kandy."
    )
    human_handoff_number: Optional[str] = Field(None, example="+94771234567")

class TenantCreate(TenantBase):
    pass

class TenantUpdate(BaseModel):
    business_name: Optional[str] = None
    whatsapp_phone_number_id: Optional[str] = None
    meta_access_token: Optional[str] = None
    system_prompt: Optional[str] = None
    knowledge_base: Optional[str] = None
    human_handoff_number: Optional[str] = None

class TenantResponse(TenantBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Helper schemas for WhatsApp Webhook parsing
class WhatsAppProfile(BaseModel):
    name: Optional[str] = None

class WhatsAppContact(BaseModel):
    wa_id: str
    profile: Optional[WhatsAppProfile] = None

class WhatsAppTextMessage(BaseModel):
    body: str

class WhatsAppMessage(BaseModel):
    from_number: str = Field(..., alias="from")
    id: str
    timestamp: str
    type: str
    text: Optional[WhatsAppTextMessage] = None

    class Config:
        populate_by_name = True

class WhatsAppValueMetadata(BaseModel):
    display_phone_number: Optional[str] = None
    phone_number_id: str

class WhatsAppValue(BaseModel):
    messaging_product: str
    metadata: WhatsAppValueMetadata
    contacts: Optional[List[WhatsAppContact]] = None
    messages: Optional[List[WhatsAppMessage]] = None

class WhatsAppChange(BaseModel):
    value: WhatsAppValue
    field: str

class WhatsAppEntry(BaseModel):
    id: str
    changes: List[WhatsAppChange]

class WhatsAppWebhookPayload(BaseModel):
    object: str
    entry: List[WhatsAppEntry]
