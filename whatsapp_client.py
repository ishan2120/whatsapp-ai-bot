import logging
import httpx
from config import settings

logger = logging.getLogger("uvicorn.error")

async def send_whatsapp_message(
    phone_number_id: str,
    recipient_phone: str,
    message_text: str,
    meta_access_token: str
) -> dict:
    """
    Posts text response back to Meta's Cloud API Graph endpoint:
    https://graph.facebook.com/{version}/{phone_number_id}/messages
    """
    url = f"https://graph.facebook.com/{settings.META_GRAPH_API_VERSION}/{phone_number_id}/messages"
    
    headers = {
        "Authorization": f"Bearer {meta_access_token}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient_phone,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message_text
        }
    }

    # If using placeholder token in development/local testing, log instead of failing HTTP request
    if meta_access_token.startswith("EAA_placeholder") or "placeholder" in meta_access_token:
        logger.info(
            f"[MOCK WHATSAPP SENDER] Sending to {recipient_phone} via phone_id={phone_number_id}:\n"
            f"Message: {message_text}"
        )
        return {"status": "mock_sent", "recipient": recipient_phone, "message": message_text}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers, timeout=15.0)
            response.raise_for_status()
            res_data = response.json()
            logger.info(f"Successfully sent WhatsApp message to {recipient_phone}. Response: {res_data}")
            return res_data
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP Error sending WhatsApp message to {recipient_phone}: "
                f"{e.response.status_code} - {e.response.text}"
            )
            raise e
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message to {recipient_phone}: {str(e)}")
            raise e


async def notify_human_agent(
    phone_number_id: str,
    handoff_number: str,
    customer_phone: str,
    last_user_message: str,
    meta_access_token: str
) -> dict:
    """
    Alerts the human handoff contact when a user requests human assistance.
    """
    alert_text = (
        f"🚨 *HUMAN HANDOFF REQUEST*\n\n"
        f"Customer: {customer_phone}\n"
        f"Message: \"{last_user_message}\"\n\n"
        f"Please step in to reply directly."
    )
    return await send_whatsapp_message(
        phone_number_id=phone_number_id,
        recipient_phone=handoff_number,
        message_text=alert_text,
        meta_access_token=meta_access_token
    )
