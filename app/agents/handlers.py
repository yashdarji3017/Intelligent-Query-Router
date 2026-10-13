from app.core.logger import get_logger
from app.schemas.classification import QueryClassification, Urgency

logger = get_logger(__name__)


async def account_handler(
    query: str,
    classification: QueryClassification,
) -> str:
    """
    Handle account security, profile, and organization-related inquiries.

    Directs users to secure account settings for sensitive operations and
    credential management.

    Args:
        query: Original user query.
        classification: Classification result for the query.

    Returns:
        str: Account assistance guidance.
    """
    try:
        logger.debug("Handling account-related inquiry.")

        return (
            "Account Security & Management Notice:\n"
            "We can assist with password resets, organization membership, "
            "and profile preferences.\n"
            "To safeguard your data privacy and security, account "
            "modifications and credential lookups require verified "
            "multi-factor authentication through your account settings "
            "portal. Please visit your account dashboard to manage "
            "profile details or update credentials safely."
        )
    except Exception:
        logger.exception("Failed to handle account-related inquiry.")
        return (
            "We encountered an issue processing your account inquiry. "
            "Please try again or contact support for assistance."
        )


async def billing_handler(
    query: str,
    classification: QueryClassification,
) -> str:
    """
    Handle billing, subscription, invoice, and payment-related inquiries.

    Provides general billing guidance and directs users to the secure
    billing dashboard for payment instrument changes.

    Args:
        query: Original user query.
        classification: Classification result for the query.

    Returns:
        str: Billing assistance guidance.
    """
    try:
        logger.debug("Handling billing-related inquiry.")

        return (
            "Billing & Subscription Assistance:\n"
            "We can help answer questions regarding plan tiers, invoice "
            "statements, and payment methods.\n"
            "For your financial protection, automated agents do not "
            "directly process charges or modify payment instruments. "
            "Please review your itemized invoice or update payment "
            "methods securely via your Billing & Invoices dashboard."
        )
    except Exception:
        logger.exception("Failed to handle billing-related inquiry.")
        return (
            "We encountered an issue processing your billing inquiry. "
            "Please try again or contact billing support for assistance."
        )


async def complex_handler(
    query: str,
    classification: QueryClassification,
) -> str:
    """
    Handle requests that involve multiple steps or interconnected tasks.

    Outlines a structured approach for decomposing requirements, resolving
    dependencies, and validating outcomes before production changes.

    Args:
        query: Original user query.
        classification: Classification result for the query.

    Returns:
        str: Recommended resolution plan.
    """
    try:
        logger.debug("Handling complex multi-step inquiry.")

        return (
            "Complex Request Resolution Plan:\n"
            "Your request involves multi-step or multifaceted "
            "considerations. Here is our recommended approach:\n"
            "1. Requirement Decomposition: Identify individual components, "
            "such as technical requirements, access permissions, and "
            "billing tiers.\n"
            "2. Step-by-Step Execution: Resolve prerequisite dependencies "
            "before applying downstream changes.\n"
            "3. Verification & Validation: Confirm each step's outcome "
            "in a staging environment before production rollout.\n"
            "If you would like to proceed with a specific phase, please "
            "specify which step to focus on first."
        )
    except Exception:
        logger.exception("Failed to handle complex inquiry.")
        return (
            "We encountered an issue preparing a resolution plan. "
            "Please describe the main outcome you want to achieve."
        )


async def fallback_handler(
    query: str,
    classification: QueryClassification,
) -> str:
    """
    Handle queries that cannot be confidently routed to a specific category.

    Requests additional information when clarification is needed or asks
    the user to identify the relevant support category.

    Args:
        query: Original user query.
        classification: Classification result containing routing context.

    Returns:
        str: Clarification request or fallback guidance.
    """
    try:
        reason = getattr(classification, "reason", None)
        requires_clarification = getattr(
            classification,
            "requires_clarification",
            False,
        )
        reason_note = f" (Context: {reason})" if reason else ""

        logger.debug(
            "Handling fallback inquiry: requires_clarification=%s",
            requires_clarification,
        )

        if requires_clarification:
            return (
                "I would like to help, but your request needs more "
                f"clarification{reason_note}. Could you please provide "
                "more specific details, such as the exact error message, "
                "the account or billing action you are trying to take, "
                "or the steps that led up to this?"
            )

        return (
            "I'm not quite sure how to best categorize or route your "
            f"query{reason_note}. Could you please clarify whether this "
            "is related to Technical Support, Account Administration, "
            "Billing & Payments, or General Information?"
        )
    except Exception:
        logger.exception("Failed to handle fallback inquiry.")
        return (
            "Could you please provide more details about your request "
            "so I can direct you to the appropriate assistance?"
        )


async def general_handler(
    query: str,
    classification: QueryClassification,
) -> str:
    """
    Handle greetings and general inquiries that do not require specialized
    account, billing, or technical assistance.

    Args:
        query: Original user query.
        classification: Classification result for the query.

    Returns:
        str: General response appropriate to the inquiry.
    """
    try:
        query_lower = query.strip().lower()

        greetings = (
            "hello",
            "hi",
            "hey",
            "good morning",
            "good evening",
            "good afternoon",
        )

        if any(greeting in query_lower for greeting in greetings):
            logger.debug("Handling greeting.")
            return (
                "Hello! I am your AI assistant. How can I help you today? "
                "You can ask me technical, account, billing, or general "
                "inquiries."
            )

        if "how are you" in query_lower:
            logger.debug("Handling conversational inquiry.")
            return (
                "I'm doing well, thank you! How can I assist you "
                "with your queries today?"
            )

        logger.debug("Handling general inquiry.")
        return (
            "Thank you for reaching out. Based on your general inquiry, "
            "I can help with questions about your account, services, "
            "or technical integrations. Please share any specific details "
            "you would like assistance with."
        )
    except Exception:
        logger.exception("Failed to handle general inquiry.")
        return (
            "Thank you for reaching out. Could you please provide more "
            "details about what you need help with?"
        )


async def technical_handler(
    query: str,
    classification: QueryClassification,
) -> str:
    """
    Handle technical questions and potential production incidents.

    Provides incident-oriented troubleshooting guidance for high-priority
    issues and requests diagnostic details for routine technical questions.

    Args:
        query: Original user query.
        classification: Classification result containing urgency information.

    Returns:
        str: Technical troubleshooting guidance.
    """
    try:
        urgency = getattr(classification, "urgency", None)
        is_urgent = urgency in (
            Urgency.CRITICAL,
            Urgency.HIGH,
            "critical",
            "high",
        )

        logger.info(
            "Handling technical inquiry: urgent=%s",
            is_urgent,
        )

        if is_urgent:
            return (
                "⚠️ Priority Technical Incident Detected.\n"
                "1. Review available engineering diagnostics and "
                "application telemetry to assess the issue.\n"
                "2. If this is a production outage or API disruption, "
                "verify endpoint availability, review response codes "
                "(5xx versus 4xx), and inspect application logs for "
                "error traces.\n"
                "3. If errors persist, provide recent request IDs, "
                "affected endpoints, timestamps, and relevant error "
                "messages to help isolate the root cause."
            )

        return (
            "Technical Support Analysis:\n"
            "Let's investigate your technical question or issue. "
            "To provide a precise solution, please share relevant details "
            "such as API endpoints, error messages or stack traces, "
            "expected versus actual behavior, and your configuration "
            "environment."
        )
    except Exception:
        logger.exception("Failed to handle technical inquiry.")
        return (
            "We encountered an issue preparing technical guidance. "
            "Please share the affected endpoint, error message, and "
            "expected behavior so the issue can be investigated."
        )