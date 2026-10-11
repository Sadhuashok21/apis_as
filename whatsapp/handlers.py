import re
import logging
from typing import Dict, Any, Optional
from django.utils import timezone
from .models import WhatsAppContact
from .services import send_whatsapp_text, send_whatsapp_interactive_buttons
from .ai_service import generate_ai_reply

logger = logging.getLogger("whatsapp.handler")

MAIN_MENU_TEXT = """Welcome to SkilTrix! 👋

Your coding and learning assistant.

Choose an option:
1. Learn Python
2. Learn Java
3. Practice DSA
4. Code Lab
5. Mock Interviews
6. Course Information
7. Contact Support

Reply with a number (1-7) or topic name.
Type 'menu' anytime to return here."""


def get_skiltrix_stats() -> Dict[str, Any]:
    """Dynamically fetches learning statistics from existing SkilTrix models."""
    stats = {"problems_count": 100, "courses_count": 15, "assessments_count": 20}
    try:
        from skiltrix.models import CodingProblems, Courses, CodingAssessment
        stats["problems_count"] = CodingProblems.objects.filter(status="active").count() or 100
        stats["courses_count"] = Courses.objects.filter(status="active").count() or 15
        stats["assessments_count"] = CodingAssessment.objects.filter(status="active").count() or 20
    except Exception as exc:
        logger.debug("SkilTrix model lookup deferred: %s", exc)
    return stats


def handle_incoming_message(
    contact: WhatsAppContact,
    incoming_text: str,
    raw_message_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Main conversational dispatcher for incoming WhatsApp user messages.
    Supports greeting detection, numerical menu selections, natural language queries,
    account linking, SkilTrix platform deep-links, and optional AI mentoring.
    """
    text = (incoming_text or "").strip()
    norm = text.lower()
    contact.last_incoming_at = timezone.now()
    contact.save(update_fields=["last_incoming_at", "updated_at"])

    # 1. Greetings / Menu Reset
    if norm in ("hi", "hello", "hey", "start", "menu", "help", "options", "restart", "home"):
        contact.current_state = "MAIN_MENU"
        contact.save(update_fields=["current_state", "updated_at"])
        return send_whatsapp_text(contact.wa_id, MAIN_MENU_TEXT, contact=contact)

    # 2. Account Linking Command: "link <email>" or "login <email>"
    link_match = re.match(r"^(?:link|connect|login)\s+([\w\.\-\+]+@[\w\.\-]+\.\w+)$", norm)
    if link_match:
        return _handle_account_link(contact, link_match.group(1))

    # 3. User Profile / Status Check
    if norm in ("profile", "status", "my account", "account"):
        return _handle_profile_check(contact)

    # 4. Menu Selection: 1. Learn Python
    if norm in ("1", "python", "learn python", "py", "python course", "python tutorials"):
        return _handle_python_option(contact)

    # 5. Menu Selection: 2. Learn Java
    if norm in ("2", "java", "learn java", "java course", "java tutorials"):
        return _handle_java_option(contact)

    # 6. Menu Selection: 3. Practice DSA
    if norm in ("3", "dsa", "practice dsa", "data structures", "algorithms", "practice"):
        return _handle_dsa_option(contact)

    # 7. Menu Selection: 4. Code Lab
    if norm in ("4", "code lab", "codelab", "compiler", "ide", "editor", "online compiler"):
        return _handle_codelab_option(contact)

    # 8. Menu Selection: 5. Mock Interviews / Assessments
    if norm in ("5", "mock", "mock interviews", "mock interview", "interviews", "assessment", "assessments"):
        return _handle_mock_option(contact)

    # 9. Menu Selection: 6. Course Information
    if norm in ("6", "course information", "courses", "catalog", "all courses", "curriculum"):
        return _handle_courses_option(contact)

    # 10. Menu Selection: 7. Contact Support
    if norm in ("7", "support", "contact", "contact support", "helpdesk", "issue"):
        return _handle_support_option(contact)

    # 11. Optional AI Mentoring Attempt
    ai_reply = generate_ai_reply(text, user_name=contact.profile_name)
    if ai_reply:
        return send_whatsapp_text(contact.wa_id, ai_reply, contact=contact)

    # 12. Fallback for Unrecognized Input
    fallback_text = (
        "Sorry, I didn't recognize that option. 🤔\n\n"
        "Please choose a number from 1 to 7 or type a topic:\n"
        "1. Learn Python\n"
        "2. Learn Java\n"
        "3. Practice DSA\n"
        "4. Code Lab\n"
        "5. Mock Interviews\n"
        "6. Course Information\n"
        "7. Contact Support\n\n"
        "💡 Type *menu* anytime to view the main menu."
    )
    return send_whatsapp_text(contact.wa_id, fallback_text, contact=contact)


# ─── Option Handlers ──────────────────────────────────────────────────────────

def _handle_python_option(contact: WhatsAppContact) -> Dict[str, Any]:
    contact.current_state = "PYTHON_INFO"
    contact.save(update_fields=["current_state", "updated_at"])
    msg = (
        "🐍 *Python Learning Track on SkilTrix*\n\n"
        "Master Python from basic syntax to advanced full-stack development:\n\n"
        "• *Fundamentals:* Variables, loops, functions, lists & dicts\n"
        "• *OOP:* Classes, inheritance, polymorphism, encapsulation\n"
        "• *Web & Backend:* Python Django, Flask, REST APIs\n"
        "• *Interactive Coding:* 'Try It Yourself' sandboxes inside every lesson\n\n"
        "🌐 Start learning now: https://skiltrix.ascentracoresolutions.com/tutorials/python\n\n"
        "Reply with another number (1-7) or type *menu*."
    )
    return send_whatsapp_text(contact.wa_id, msg, contact=contact)


def _handle_java_option(contact: WhatsAppContact) -> Dict[str, Any]:
    contact.current_state = "JAVA_INFO"
    contact.save(update_fields=["current_state", "updated_at"])
    msg = (
        "☕ *Java Enterprise & Cloud Track on SkilTrix*\n\n"
        "Complete beginner to advanced enterprise roadmap:\n\n"
        "• *Core Java:* Syntax, methods, OOP concepts, exceptions\n"
        "• *Collections & Streams:* Lists, Maps, Sets, lambdas & functional streams\n"
        "• *Advanced:* Multithreading, JDBC, Spring Boot microservices\n"
        "• *Interview Prep:* 150+ solved Java interview questions\n\n"
        "🌐 Explore Java tutorials: https://skiltrix.ascentracoresolutions.com/tutorials/java\n\n"
        "Reply with another number (1-7) or type *menu*."
    )
    return send_whatsapp_text(contact.wa_id, msg, contact=contact)


def _handle_dsa_option(contact: WhatsAppContact) -> Dict[str, Any]:
    stats = get_skiltrix_stats()
    contact.current_state = "DSA_INFO"
    contact.save(update_fields=["current_state", "updated_at"])
    msg = (
        f"⚡ *Data Structures & Algorithms (DSA)*\n\n"
        f"Sharpen your problem-solving skills across {stats['problems_count']}+ curated coding challenges:\n\n"
        "• *Arrays & Strings:* Two pointers, sliding window\n"
        "• *Linked Lists, Stacks & Queues*\n"
        "• *Trees & Graphs:* BFS, DFS, Dijkstra, Topo-sort\n"
        "• *Dynamic Programming & Greedy Approaches*\n\n"
        "💻 Run test cases against our live sandboxed judge:\n"
        "🌐 Practice now: https://skiltrix.ascentracoresolutions.com/practice\n\n"
        "Reply with another number (1-7) or type *menu*."
    )
    return send_whatsapp_text(contact.wa_id, msg, contact=contact)


def _handle_codelab_option(contact: WhatsAppContact) -> Dict[str, Any]:
    contact.current_state = "CODELAB_INFO"
    contact.save(update_fields=["current_state", "updated_at"])
    msg = (
        "💻 *SkilTrix Code Lab & Cloud IDE*\n\n"
        "Write, run, and debug code right inside your browser without local setup:\n\n"
        "• Multi-language support: Python, Java, C++, C#, Go, Rust, PHP, SQL & Web\n"
        "• Live in-browser compilation & execution\n"
        "• Interactive SQL database playground\n"
        "• Share code snippets and collaborate with peers\n\n"
        "🌐 Launch Code Lab: https://skiltrix.ascentracoresolutions.com/codelab\n\n"
        "Reply with another number (1-7) or type *menu*."
    )
    return send_whatsapp_text(contact.wa_id, msg, contact=contact)


def _handle_mock_option(contact: WhatsAppContact) -> Dict[str, Any]:
    stats = get_skiltrix_stats()
    contact.current_state = "MOCK_INFO"
    contact.save(update_fields=["current_state", "updated_at"])
    msg = (
        "🎯 *Company Mock Interviews & Placement Assessments*\n\n"
        f"Prepare for top tech companies with {stats['assessments_count']}+ realistic assessments:\n\n"
        "• Timed online coding tests mimicking real hiring platforms\n"
        "• Comprehensive test-suite evaluation and complexity analytics\n"
        "• Curated company blueprints (TCS, Infosys, Amazon, Microsoft, etc.)\n"
        "• Video solution walk-throughs and diagnostic reports\n\n"
        "🌐 Take a mock assessment: https://skiltrix.ascentracoresolutions.com/placement-preparation\n\n"
        "Reply with another number (1-7) or type *menu*."
    )
    return send_whatsapp_text(contact.wa_id, msg, contact=contact)


def _handle_courses_option(contact: WhatsAppContact) -> Dict[str, Any]:
    contact.current_state = "COURSES_INFO"
    contact.save(update_fields=["current_state", "updated_at"])

    # Query active courses if available
    course_items = []
    try:
        from skiltrix.models import Courses
        active_courses = Courses.objects.filter(status="active")[:4]
        for c in active_courses:
            course_items.append(f"• *{c.title}* ({c.level or 'All levels'})")
    except Exception:
        pass

    course_list_str = "\n".join(course_items) if course_items else (
        "• Full Stack Web Development (React & Django)\n"
        "• Java Enterprise & Cloud Architecture\n"
        "• Data Structures, Algorithms & Problem Solving\n"
        "• Complete Python for Developers"
    )

    msg = (
        "📚 *SkilTrix Featured Courses*\n\n"
        f"{course_list_str}\n\n"
        "Every course includes video lessons, interactive quizzes, downloadable notes, and verified certificates.\n\n"
        "🌐 Browse catalog: https://skiltrix.ascentracoresolutions.com/courses\n\n"
        "Reply with another number (1-7) or type *menu*."
    )
    return send_whatsapp_text(contact.wa_id, msg, contact=contact)


def _handle_support_option(contact: WhatsAppContact) -> Dict[str, Any]:
    contact.current_state = "SUPPORT_INFO"
    contact.save(update_fields=["current_state", "updated_at"])
    msg = (
        "🤝 *SkilTrix Support & Assistance*\n\n"
        "We are here to help you succeed in your learning journey!\n\n"
        "• 📧 *Email:* support@ascentracoresolutions.com\n"
        "• 🌐 *Help Center:* https://skiltrix.ascentracoresolutions.com/about\n"
        "• 💬 *Community Forum:* https://skiltrix.ascentracoresolutions.com/community\n\n"
        "To link your SkilTrix account with WhatsApp, send:\n"
        "*link your_email@example.com*\n\n"
        "Type *menu* to return to the options."
    )
    return send_whatsapp_text(contact.wa_id, msg, contact=contact)


def _handle_account_link(contact: WhatsAppContact, email: str) -> Dict[str, Any]:
    """Links contact's WhatsApp number to existing SkilTrix / sfs user account."""
    try:
        from sfs.models import AllUsers
        user = AllUsers.objects.filter(email__iexact=email).first()
        if not user:
            return send_whatsapp_text(
                contact.wa_id,
                f"No SkilTrix account found with email *{email}*.\n"
                f"Please register first at https://skiltrix.ascentracoresolutions.com or type *menu*.",
                contact=contact
            )

        contact.user = user
        contact.save(update_fields=["user", "updated_at"])
        user_name = user.name or user.username
        success_msg = (
            f"🎉 *Account Connected!*\n\n"
            f"Welcome back, *{user_name}*!\n"
            f"Your WhatsApp number is now linked to your SkilTrix account ({email}).\n\n"
            f"Type *profile* to see your learning status or *menu* to explore courses."
        )
        return send_whatsapp_text(contact.wa_id, success_msg, contact=contact)
    except Exception as exc:
        logger.error("Error during account linking: %s", exc)
        return send_whatsapp_text(
            contact.wa_id,
            "An error occurred while linking your account. Please try again later or contact support.",
            contact=contact
        )


def _handle_profile_check(contact: WhatsAppContact) -> Dict[str, Any]:
    """Displays user's learning metrics if linked."""
    if not contact.user:
        msg = (
            "ℹ️ *No Linked SkilTrix Account*\n\n"
            "Your WhatsApp number is not yet linked to a SkilTrix account.\n\n"
            "To connect your account, send:\n"
            "*link your_email@example.com*\n\n"
            "Type *menu* to view learning options."
        )
        return send_whatsapp_text(contact.wa_id, msg, contact=contact)

    user = contact.user
    user_name = user.name or user.username
    msg = (
        f"👤 *SkilTrix Profile: {user_name}*\n\n"
        f"• Email: {user.email}\n"
        f"• Account Status: Active\n"
        f"• Portal: https://skiltrix.ascentracoresolutions.com/profile\n\n"
        f"Type *menu* to return to the main menu."
    )
    return send_whatsapp_text(contact.wa_id, msg, contact=contact)

