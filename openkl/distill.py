"""
Memory distillation operations for OpenKL.
"""

from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

from .citations import CitationManager
from .db import get_connection
from .memory import MemoryManager

console = Console()


class DistillationManager:
    """Manages memory distillation prompts and API for agents."""

    def __init__(self, base_path: Path = Path.home() / ".ok"):
        self.base_path = base_path
        self.citation_manager = CitationManager()
        self.memory_manager = MemoryManager(base_path)

    def get_distillation_prompt(self, prompt_type: str = "extract-facts") -> str:
        """Get a distillation prompt for agents to use with LLMs."""
        prompts = {
            "extract-facts": """Extract key facts and important details from the following content. Focus on concrete information, numbers, dates, and specific claims.

Content:
{content}

Instructions:
- Extract the most important factual information
- Include specific details, numbers, dates, and concrete claims
- Avoid opinions or interpretations
- Format as clear, concise bullet points
- Each fact should be standalone and verifiable

Output format:
- [Fact 1]
- [Fact 2]
- [Fact 3]""",
            "identify-patterns": """Identify recurring patterns, principles, and common approaches from the following content. Focus on generalizable insights.

Content:
{content}

Instructions:
- Look for recurring themes, approaches, or principles
- Identify patterns that could apply to similar situations
- Extract generalizable insights and best practices
- Focus on "how" and "why" rather than specific details
- Format as clear principles or patterns

Output format:
- Pattern/Principle 1: [Description]
- Pattern/Principle 2: [Description]
- Pattern/Principle 3: [Description]""",
            "summarize-insights": """Create a high-level summary of the key insights from the following content. Focus on the main takeaways and implications.

Content:
{content}

Instructions:
- Identify the main themes and key takeaways
- Focus on implications and broader significance
- Synthesize information into coherent insights
- Avoid repeating specific details
- Write in a clear, accessible style

Output format:
[2-3 paragraph summary focusing on key insights and implications]""",
            "extract-relationships": """Identify relationships and connections between concepts in the following content. Focus on how different ideas relate to each other.

Content:
{content}

Instructions:
- Identify how different concepts, ideas, or entities relate
- Look for cause-effect relationships, dependencies, and interactions
- Note hierarchical or categorical relationships
- Identify complementary or conflicting concepts
- Format as relationship statements

Output format:
- [Concept A] → [Relationship] → [Concept B]
- [Concept C] depends on [Concept D]
- [Concept E] is a type of [Concept F]""",
            "extract-entities": """Extract important entities (people, organizations, technologies, concepts) and their key properties from the following content.

Content:
{content}

Instructions:
- Identify important entities (people, organizations, technologies, concepts)
- Extract key properties, attributes, or characteristics of each entity
- Note relationships between entities
- Focus on entities that are central to the content
- Format as entity-property pairs

Output format:
- [Entity Name]: [Key properties and characteristics]
- [Entity Name]: [Key properties and characteristics]
- [Entity Name]: [Key properties and characteristics]""",
            "memory-synthesis": """Synthesize the following content into a concise, actionable memory entry. Focus on creating a useful reference for future use.

Content:
{content}

Instructions:
- Create a concise summary that captures the essence
- Focus on actionable insights and key takeaways
- Use clear, direct language
- Include important context and implications
- Make it useful as a future reference
- Keep it under 200 words

Output format:
[Concise, actionable memory entry that captures key insights and context]""",
        }

        return prompts.get(prompt_type, prompts["extract-facts"])

    def create_memory_from_distillation(
        self,
        distilled_content: str,
        source_citations: list[str],
        tags: Optional[list[str]] = None,
        topics: Optional[list[str]] = None,
    ) -> str:
        """Create a memory from agent-distilled content with proper relationships."""
        if not distilled_content.strip():
            console.print("[red]No distilled content provided[/red]")
            return ""

        # Create memory (clean text for storage)
        clean_content = distilled_content.replace("\n", " ").replace("\r", " ")
        memory_id = self.memory_manager.add(
            clean_content, tags=tags or [], topics=topics or []
        )

        # Create graph relationships to source citations
        self._create_distillation_relationships(memory_id, source_citations)

        console.print(f"[green]✓[/green] Memory created from distillation: {memory_id}")
        return memory_id

    def _create_distillation_relationships(
        self, memory_id: str, source_citations: list[str]
    ) -> None:
        """Create graph relationships for distilled memory."""
        conn = get_connection()

        # Create DerivedFrom relationships to source chunks
        for cite_id in source_citations:
            try:
                # Extract chunk ID from citation
                if "#" in cite_id:
                    chunk_id = cite_id
                else:
                    # Try to find chunk ID from citation
                    citation = self.citation_manager.open_citation(cite_id)
                    if citation and "id" in citation:
                        chunk_id = citation["id"]
                    else:
                        continue

                # Create relationship
                conn.execute(
                    """
                    MATCH (m:MemoryNote {id: $memory_id}), (c:Chunk {id: $chunk_id})
                    CREATE (m)-[:DerivedFrom]->(c)
                    """,
                    {"memory_id": memory_id, "chunk_id": chunk_id},
                )
            except Exception as e:
                console.print(
                    f"[yellow]Warning: Failed to create relationship for {cite_id}: {e}[/yellow]"
                )

    def list_distillation_prompts(self) -> None:
        """List available distillation prompts."""
        prompts = {
            "extract-facts": "Extract key facts and important details",
            "identify-patterns": "Find recurring patterns and principles",
            "summarize-insights": "Create high-level summaries",
            "extract-relationships": "Identify connections between concepts",
            "extract-entities": "Find important entities and properties",
            "memory-synthesis": "Synthesize into actionable memory entry",
        }

        table = Table(title="Available Distillation Prompts")
        table.add_column("Prompt", style="cyan")
        table.add_column("Description", style="white")

        for prompt, description in prompts.items():
            table.add_row(prompt, description)

        console.print(table)

    def get_prompt_template(self, prompt_type: str) -> str:
        """Get a prompt template for agents to use."""
        prompt = self.get_distillation_prompt(prompt_type)

        # Show the template with placeholder
        console.print(f"[bold]Distillation Prompt Template:[/bold] {prompt_type}")
        console.print("=" * 50)
        console.print(prompt)
        console.print("=" * 50)
        console.print(
            "\n[bold]Usage:[/bold] Replace {content} with the actual content to distill"
        )

        return prompt
