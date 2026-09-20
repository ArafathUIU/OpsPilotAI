"""Tools for searching long-term episodic incident memory and historical postmortems."""

from typing import Any

from src.memory.episodic import EpisodicMemoryManager
from src.tools.base import BaseTool


class SearchIncidentMemoryTool(BaseTool):
    """Tool to search previous incident postmortems using semantic vector similarity."""

    name: str = "search_incident_memory"
    description: str = (
        "Search historical incident postmortems, proven root causes, and remediation actions "
        "using semantic similarity to the current failure symptoms."
    )
    required_role: str = "VIEWER"

    def __init__(self, memory_manager: EpisodicMemoryManager | None = None) -> None:
        self.memory_manager = memory_manager or EpisodicMemoryManager()

    async def _run(
        self,
        query: str,
        service: str | None = None,
        limit: int = 3,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Searches episodic memory and formats relevant matches."""
        results = await self.memory_manager.search_similar_incidents(
            query=query,
            service=service,
            top_k=limit,
        )

        matches = []
        for r in results:
            doc = r.document
            matches.append(
                {
                    "incident_id": doc.id,
                    "title": doc.metadata.get("title", ""),
                    "service": doc.metadata.get("service", ""),
                    "similarity_score": round(r.similarity_score, 4),
                    "root_cause": doc.metadata.get("root_cause", ""),
                    "remediation_steps": doc.metadata.get("remediation_steps", []),
                    "summary": doc.metadata.get("summary", ""),
                }
            )

        formatted_context = self.memory_manager.format_memories_for_prompt(results)
        return {
            "query": query,
            "service_filter": service,
            "match_count": len(matches),
            "matches": matches,
            "formatted_context": formatted_context,
        }
