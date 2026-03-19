"""pydantic-ai tools for PolicyAgent."""

import logging
from pydantic_ai import RunContext
from app.agents.dependencies import AgentDependencies

logger = logging.getLogger(__name__)


async def retrieve_policy_sections(
    ctx: RunContext[AgentDependencies], query: str, k: int = 3
) -> str:
    """
    Retrieve the most relevant policy sections for the query using semantic search.
    Returns formatted text ready for the LLM.
    Args:
        query: The user's policy question
        k: Number of sections to retrieve (default 3)
    """
    vector_store = getattr(ctx.deps, "vector_store", None)
    if vector_store is None:
        return _db_fallback(ctx.deps.db, query)

    chunks = vector_store.search(query, k=k)
    if not chunks:
        return "No relevant policy sections found."

    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(
            f"[Section {i} — {c.policy_type} (score: {c.score:.2f})]:\n{c.text}"
        )
    return "\n\n".join(parts)


def _db_fallback(db, query: str) -> str:
    from sqlalchemy import or_

    from app.models.policy import Policy

    keywords = query.lower().split()
    if not keywords:
        return "No matching policies found."

    # Build SQL WHERE filters instead of loading all rows and filtering in Python
    conditions = []
    for kw in keywords:
        pattern = f"%{kw}%"
        conditions.append(Policy.description.ilike(pattern))
        conditions.append(Policy.conditions.ilike(pattern))

    policies = db.query(Policy).filter(or_(*conditions)).limit(3).all()

    if not policies:
        return "No matching policies found."

    results = [f"{p.policy_type}: {p.description}\n{p.conditions}" for p in policies]
    return "\n\n".join(results)
