"""
Graph operations using Kùzu DB for OpenKL.
"""

from typing import Any

from rich.console import Console
from rich.json import JSON
from rich.table import Table

from .db import get_connection

console = Console()


class GraphManager:
    """Manages graph operations and Cypher queries."""

    def __init__(self):
        pass

    def run_cypher(
        self, query: str, params: dict[str, Any] = None
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query and return results."""
        if params is None:
            params = {}

        conn = get_connection()

        try:
            result = conn.execute(query, params)

            # Convert result to list of dictionaries
            results = []
            for row in result:
                # Convert row to dictionary
                row_dict = {}
                for i, value in enumerate(row):
                    # Get column name from result description if available
                    if hasattr(result, "get_column_names"):
                        col_name = result.get_column_names()[i]
                    else:
                        col_name = f"col_{i}"
                    row_dict[col_name] = value
                results.append(row_dict)

            return results

        except Exception as e:
            console.print(f"[red]Error executing Cypher query:[/red] {e}")
            return []

    def get_entity_stats(self) -> dict[str, int]:
        """Get basic statistics about the graph."""
        conn = get_connection()

        stats = {}

        # Count nodes
        result = conn.execute("MATCH (n) RETURN labels(n) as label, count(n) as count")
        for row in result:
            label = row[0][0] if row[0] else "Unknown"
            stats[f"{label}_count"] = row[1]

        # Count relationships - Kùzu doesn't have type() function, so we'll count by relationship name
        rel_types = ["HAS_CHUNK", "Mentions", "MemMentions", "DerivedFrom", "HasTopic"]
        for rel_type in rel_types:
            result = conn.execute(
                f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
            )
            count = list(result)[0][0] if result else 0
            stats[f"{rel_type}_count"] = count

        return stats

    def find_related_entities(self, entity_name: str) -> list[dict[str, Any]]:
        """Find entities related to a given entity name."""
        query = """
        MATCH (e:Entity {name: $name})-[r]-(related)
        RETURN labels(related) as type, related.name as name, type(r) as relationship
        ORDER BY relationship
        """

        return self.run_cypher(query, {"name": entity_name})

    def get_memory_entities(self, memory_id: str) -> list[dict[str, Any]]:
        """Get entities mentioned in a specific memory."""
        query = """
        MATCH (m:MemoryNote {id: $id})-[:MemMentions]->(e:Entity)
        RETURN e.name as name, e.type as type
        ORDER BY e.name
        """

        return self.run_cypher(query, {"id": memory_id})

    def print_results(self, results: list[dict[str, Any]], json_output: bool = False):
        """Print query results."""
        if not results:
            console.print("[yellow]No results found[/yellow]")
            return

        if json_output:
            console.print(JSON.from_data(results))
        else:
            # Create table with dynamic columns
            table = Table(title="Graph Query Results")

            if results:
                # Process first result to determine columns
                first_result = self._process_kuzu_result(results[0])
                columns = [
                    col
                    for col in first_result.keys()
                    if not col.endswith("vec") and col != "vec"
                ]

                for col in columns:
                    table.add_column(col, style="cyan")

                # Add rows
                for result in results:
                    processed_result = self._process_kuzu_result(result)
                    row_values = []
                    for col in columns:
                        value = processed_result.get(col, "")
                        # Clean string representation if it contains vectors
                        if isinstance(value, str) and "vec" in value:
                            value = self._clean_string_representation(value)
                        row_values.append(str(value))
                    table.add_row(*row_values)

            console.print(table)

    def _process_kuzu_result(self, result) -> dict[str, Any]:
        """Process a Kùzu result object and filter out vector fields."""
        if hasattr(result, "__dict__"):
            # Handle Kùzu object - if it's a single column with an object, expand it
            result_dict = {
                k: v for k, v in result.__dict__.items() if not k.startswith("_")
            }

            # If we have a single column that contains an object, expand it
            if len(result_dict) == 1:
                single_key = list(result_dict.keys())[0]
                single_value = result_dict[single_key]
                if hasattr(single_value, "__dict__"):
                    # Expand the object
                    result_dict = {
                        k: v
                        for k, v in single_value.__dict__.items()
                        if not k.startswith("_")
                    }
        else:
            result_dict = dict(result) if hasattr(result, "items") else result

        # Filter out vector fields cleanly
        filtered_result = {}
        for k, v in result_dict.items():
            if k.endswith("vec") or k == "vec":
                continue

            # If the value is a Kùzu object, recursively process it
            if hasattr(v, "__dict__"):
                v = self._process_kuzu_result(v)
            # If the value is a list (like a vector), skip it
            elif isinstance(v, list) and len(v) > 10:  # Likely a vector
                continue

            filtered_result[k] = v

        return filtered_result

    def _clean_string_representation(self, obj_str: str) -> str:
        """Clean string representation of Kùzu objects to remove vectors."""
        import re

        # Remove vector fields from string representation - more aggressive approach
        # Match 'vec': [ followed by any characters until the closing ]
        obj_str = re.sub(
            r"'vec':\s*\[.*?\]", "'vec': [<truncated>]", obj_str, flags=re.DOTALL
        )
        # Also handle cases where vec might be at the end
        obj_str = re.sub(
            r",\s*'vec':\s*\[.*?\]", ", 'vec': [<truncated>]", obj_str, flags=re.DOTALL
        )
        return obj_str
