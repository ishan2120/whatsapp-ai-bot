import logging
import re
from typing import List, Dict, Tuple
from openai import AsyncOpenAI
from config import settings

logger = logging.getLogger("uvicorn.error")

PDF_PRICE_LIST_URL = "https://whatsapp-ai-bot-3f6n.onrender.com/static/pdfs/Price_List.pdf"
PDF_BANQUETS_URL = "https://whatsapp-ai-bot-3f6n.onrender.com/static/pdfs/Wasala_Banquets.pdf"
PDF_REGI_URL = "https://whatsapp-ai-bot-3f6n.onrender.com/static/pdfs/REGI_2026.pdf"

def get_openai_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

def smart_knowledge_base_search(user_message: str, knowledge_base: str, system_prompt: str) -> str:
    """
    Smart Local Knowledge-Base AI Simulator with Multilingual PDF Document Triggers.
    Matches queries in English, Sinhala, or Singlish and attaches official PDFs.
    """
    msg = user_message.lower().strip()
    kb_lines = [line.strip() for line in knowledge_base.split("\n") if line.strip()]

    # Detect language intent
    is_singlish = any(w in msg for w in ["macho", "thiyenawada", "kohomada", "gaana", "kiyada", "ekak", "apita", "hari", "sinhala", "ewanna"])
    is_sinhala = any('\u0d80' <= c <= '\u0dff' for c in user_message)

    # Human handoff check
    is_handoff_words = any(w in msg for w in ["human", "agent", "manager", "person", "staff", "receptionist", "call", "help me"])

    # Document Trigger Checks
    pdf_tag = ""
    if any(w in msg for w in ["registration", "register", "regi", "civil", "2026 regi", "රෙජිස්ට්‍රේෂන්", "රෙජිස්ටර්"]):
        pdf_tag = f" [SEND_DOC: {PDF_REGI_URL} | REGI 2026.pdf | Wasala Nature Resort - Registration Packages 2026]"
    elif any(w in msg for w in ["menu", "items", "compliment", "complimentary", "terms", "policy", "policies", "details", "banquet", "කෑම", "මෙන්නු", "කොන්දේසි"]):
        pdf_tag = f" [SEND_DOC: {PDF_BANQUETS_URL} | Wasala Banquets.pdf | Wasala Nature Resort - Full Banquet & Menu Details]"
    elif any(w in msg for w in ["price", "prices", "list", "cost", "quotation", "rate", "rates", "budget", "ගණන්", "මිල", "ලැයිස්තුව", "ganan", "mila"]):
        pdf_tag = f" [SEND_DOC: {PDF_PRICE_LIST_URL} | Price List.pdf | Wasala Nature Resort - Official Wedding Price List]"

    # Match topic keywords
    matched_lines = []
    
    # 1. Price / Package queries
    if any(w in msg for w in ["price", "prices", "rate", "cost", "pax", "silver", "gold", "premier", "ballroom", "starlight", "ganan", "kiyada"]):
        for line in kb_lines:
            if any(k in line.lower() for k in ["pax", "silver", "gold", "premier", "ballroom", "starlight", "plate", "per head", "rs.", "$"]):
                matched_lines.append(f"• {line}")

    # 2. Details / Menu / Compliments queries
    if any(w in msg for w in ["menu", "items", "compliment", "policy", "deposit", "corkage", "music", "detail"]):
        for line in kb_lines:
            if any(k in line.lower() for k in ["menu", "extra", "deposit", "corkage", "music", "policy", "brochure"]):
                matched_lines.append(f"• {line}")

    # Build response
    if matched_lines:
        details = "\n".join(matched_lines[:6])
        if is_singlish:
            response = f"✨ *Here are your banquet & package details, Macho:*\n\n{details}\n\nI have also attached the PDF document for you below! 👇{pdf_tag}"
        elif is_sinhala:
            response = f"✨ *ඔබ ඉල්ලා සිටි මංගල පැකේජ විස්තර මෙන්න:*\n\n{details}\n\nමම ඔබ වෙනුවෙන් නිල PDF ලේඛනය පහතින් ලබා දී ඇත! 👇{pdf_tag}"
        else:
            response = f"✨ *Thank you for reaching out to Wasala Nature Resort! Here are the requested details:*\n\n{details}\n\nI have also attached the official PDF brochure for you below! 👇{pdf_tag}"
    else:
        summary = "\n".join([f"• {line}" for line in kb_lines[:5]])
        if is_singlish:
            response = f"👋 *Welcome to Wasala Nature Resort, Macho!*\n\n{summary}\n\nAttached is the requested PDF brochure for you! 👇{pdf_tag}"
        elif is_sinhala:
            response = f"👋 *සාදරයෙන් පිළිගනිමු! අපගේ මංගල පැකේජ විස්තර මෙන්න:*\n\n{summary}\n\nඅදාළ PDF ලේඛනය පහතින් අමුණා ඇත! 👇{pdf_tag}"
        else:
            response = f"👋 *Welcome to Wasala Nature Resort - Banquet & Events!*\n\n{summary}\n\nPlease find the attached official PDF document below! 👇{pdf_tag}"

    if is_handoff_words:
        response += "\n\n🚨 *A front desk manager has been notified to assist you directly.* [HUMAN_HANDOFF_REQUESTED]"

    return response


async def generate_ai_response(
    system_prompt: str,
    knowledge_base: str,
    chat_history: List[Dict[str, str]],
    user_message: str
) -> Tuple[str, bool]:
    """
    Generates AI response using OpenAI gpt-4o-mini, with automatic fallback
    to Smart Knowledge-Base Simulator if OpenAI key is unconfigured or credits exhausted.
    """
    api_key = settings.OPENAI_API_KEY.strip() if settings.OPENAI_API_KEY else ""

    # Fallback immediately if key is placeholder or empty
    if not api_key or "placeholder" in api_key:
        reply = smart_knowledge_base_search(user_message, knowledge_base, system_prompt)
        is_handoff = "[HUMAN_HANDOFF_REQUESTED]" in reply
        reply = reply.replace("[HUMAN_HANDOFF_REQUESTED]", "").strip()
        return reply, is_handoff

    # Attempt OpenAI gpt-4o-mini API call
    try:
        client = AsyncOpenAI(api_key=api_key)
        pdf_instructions = (
            "\n\n--- MULTILINGUAL PDF AUTOMATION RULES ---\n"
            "If the user asks (in English, Sinhala, or Singlish) about:\n"
            "1. WEDDING PACKAGE PRICES / RATES / COST / QUOTATIONS:\n"
            f"   Append exactly: [SEND_DOC: {PDF_PRICE_LIST_URL} | Price List.pdf | Wasala Nature Resort - Wedding Price List 2026]\n"
            "2. MENU ITEMS / COMPLIMENTARY BENEFITS / TERMS / POLICIES / BANQUET DETAILS:\n"
            f"   Append exactly: [SEND_DOC: {PDF_BANQUETS_URL} | Wasala Banquets.pdf | Wasala Nature Resort - Full Banquet & Menu Details]\n"
            "3. REGISTRATION PACKAGES / CIVIL REGISTRATION / 2026 REGISTRATION RATES:\n"
            f"   Append exactly: [SEND_DOC: {PDF_REGI_URL} | REGI 2026.pdf | Wasala Nature Resort - Registration Packages 2026]\n"
            "------------------------------------------\n"
        )
        full_system_instructions = (
            f"{system_prompt}\n\n"
            f"--- KNOWLEDGE BASE ---\n"
            f"{knowledge_base}\n"
            f"----------------------\n"
            f"{pdf_instructions}"
        )
        messages = [{"role": "system", "content": full_system_instructions}]
        for msg in chat_history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        reply_content = response.choices[0].message.content.strip()
        is_human_handoff = "[HUMAN_HANDOFF_REQUESTED]" in reply_content
        reply_content = reply_content.replace("[HUMAN_HANDOFF_REQUESTED]", "").strip()
        return reply_content, is_human_handoff

    except Exception as e:
        logger.warning(f"OpenAI API Error ({e}). Using Smart Knowledge-Base Simulator fallback.")
        reply = smart_knowledge_base_search(user_message, knowledge_base, system_prompt)
        is_handoff = "[HUMAN_HANDOFF_REQUESTED]" in reply
        reply = reply.replace("[HUMAN_HANDOFF_REQUESTED]", "").strip()
        return reply, is_handoff
