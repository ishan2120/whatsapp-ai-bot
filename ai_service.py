import logging
import re
from typing import List, Dict, Tuple
from openai import AsyncOpenAI
from config import settings

logger = logging.getLogger("uvicorn.error")

def get_openai_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

def smart_knowledge_base_search(user_message: str, knowledge_base: str, system_prompt: str) -> str:
    """
    Smart Local Knowledge-Base AI Simulator.
    Extracts relevant facts from tenant knowledge base matching user questions
    in English, Sinhala, or Singlish.
    """
    msg = user_message.lower().strip()
    kb_lines = [line.strip() for line in knowledge_base.split("\n") if line.strip()]

    # Detect language intent
    is_singlish = any(w in msg for w in ["macho", "thiyenawada", "kohomada", "gaana", "kiyada", "ekak", "apita", "hari", "sinhala"])
    is_sinhala = any('\u0d80' <= c <= '\u0dff' for c in user_message)

    # Human handoff check
    is_handoff_words = any(w in msg for w in ["human", "agent", "manager", "person", "staff", "receptionist", "call", "help me"])

    # Match topic keywords
    matched_lines = []
    
    # 1. Room / Price / Booking queries
    if any(w in msg for w in ["room", "rate", "price", "cost", "booking", "villa", "suite", "deluxe", "gaana", "kiyada", "nawathena"]):
        for line in kb_lines:
            if any(k in line.lower() for k in ["room", "suite", "villa", "deluxe", "executive", "rate", "price", "rs.", "$"]):
                matched_lines.append(f"• {line}")

    # 2. Check-in / Check-out / Time queries
    if any(w in msg for w in ["time", "check-in", "check in", "check-out", "checkout", "hours", "open", "welawa"]):
        for line in kb_lines:
            if any(k in line.lower() for k in ["check-in", "check-out", "hours", "open", "time"]):
                matched_lines.append(f"• {line}")

    # 3. Location / Address queries
    if any(w in msg for w in ["where", "location", "address", "kohedha", "place", "bentota", "kandy"]):
        for line in kb_lines:
            if any(k in line.lower() for k in ["location", "address", "road", "street", "city"]):
                matched_lines.append(f"• {line}")

    # 4. Dining / Menu / Food queries
    if any(w in msg for w in ["food", "menu", "kottu", "rice", "curry", "restaurant", "buffet", "eat", "drink", "kema"]):
        for line in kb_lines:
            if any(k in line.lower() for k in ["menu", "food", "kottu", "rice", "curry", "buffet", "dining", "restaurant", "juice"]):
                matched_lines.append(f"• {line}")

    # If specific topic matched, build formatted response
    if matched_lines:
        details = "\n".join(matched_lines)
        if is_singlish:
            response = f"✨ *Here are our details for you, Macho:*\n\n{details}\n\nAnything else you'd like to know?"
        elif is_sinhala:
            response = f"✨ *ඔබගේ ප්‍රශ්නයට අදාළ තොරතුරු මෙන්න:*\n\n{details}\n\nතවත් යමක් දැනගැනීමට අවශ්‍යද?"
        else:
            response = f"✨ *Thank you for reaching out! Here is the information you requested:*\n\n{details}\n\nHow else may we assist you today?"
    else:
        # Fallback to general knowledge base summary
        summary = "\n".join([f"• {line}" for line in kb_lines[:5]])
        if is_singlish:
            response = f"👋 *Welcome! Here is our key information, Macho:*\n\n{summary}\n\nPlease ask any specific question!"
        elif is_sinhala:
            response = f"👋 *ආයුබෝවන්! අපගේ විස්තර මෙන්න:*\n\n{summary}\n\nකරුණාකර ඕනෑම ප්‍රශ්නයක් අහන්න!"
        else:
            response = f"👋 *Welcome! Here is our information:*\n\n{summary}\n\nPlease let us know how we can help you!"

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
        full_system_instructions = (
            f"{system_prompt}\n\n"
            f"--- KNOWLEDGE BASE ---\n"
            f"{knowledge_base}\n"
            f"----------------------\n"
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
