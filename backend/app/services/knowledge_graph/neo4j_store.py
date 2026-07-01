from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.knowledge_graph import (
    Entity,
    GraphEdge,
    GraphNode,
    GraphResponse,
    Relation,
)

logger = get_logger(__name__)


class Neo4jStore:
    """Async Neo4j adapter for the per-user knowledge graph.

    Model:
      (:Paper {id, user_id, title})
      (:Entity {user_id, key, name, type})
      (Paper)-[:MENTIONS]->(Entity)
      (Entity)-[:REL {label}]->(Entity)

    Entities are keyed by ``(user_id, lower(name))`` so the same concept across
    different papers collapses to one node — which is what connects papers in the graph.
    """

    def __init__(self) -> None:
        self._driver = None

    def _get_driver(self):
        if self._driver is None:
            from neo4j import AsyncGraphDatabase

            self._driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            )
        return self._driver

    async def close(self) -> None:
        if self._driver is not None:
            await self._driver.close()
            self._driver = None

    async def ensure_constraints(self) -> None:
        driver = self._get_driver()
        async with driver.session() as session:
            await session.run(
                "CREATE CONSTRAINT paper_id IF NOT EXISTS "
                "FOR (p:Paper) REQUIRE p.id IS UNIQUE"
            )
            await session.run(
                "CREATE CONSTRAINT entity_key IF NOT EXISTS "
                "FOR (e:Entity) REQUIRE (e.user_id, e.key) IS UNIQUE"
            )

    async def upsert_graph(
        self,
        *,
        user_id: str,
        document_id: str,
        title: str,
        entities: list[Entity],
        relations: list[Relation],
    ) -> None:
        driver = self._get_driver()
        ent_params = [{"name": e.name, "type": e.type} for e in entities]
        rel_params = [
            {"source": r.source, "relation": r.relation, "target": r.target}
            for r in relations
        ]
        async with driver.session() as session:
            await session.run(
                """
                MERGE (p:Paper {id: $document_id})
                SET p.user_id = $user_id, p.title = $title
                WITH p
                UNWIND $entities AS ent
                MERGE (e:Entity {user_id: $user_id, key: toLower(ent.name)})
                SET e.name = ent.name, e.type = ent.type
                MERGE (p)-[:MENTIONS]->(e)
                """,
                document_id=document_id,
                user_id=user_id,
                title=title,
                entities=ent_params,
            )
            if rel_params:
                await session.run(
                    """
                    UNWIND $relations AS rel
                    MATCH (a:Entity {user_id: $user_id, key: toLower(rel.source)})
                    MATCH (b:Entity {user_id: $user_id, key: toLower(rel.target)})
                    MERGE (a)-[r:REL {label: rel.relation}]->(b)
                    """,
                    user_id=user_id,
                    relations=rel_params,
                )
        logger.info(
            "kg_upserted",
            document_id=document_id,
            entities=len(entities),
            relations=len(relations),
        )

    async def delete_document(self, *, user_id: str, document_id: str) -> None:
        driver = self._get_driver()
        async with driver.session() as session:
            await session.run(
                "MATCH (p:Paper {id: $document_id}) DETACH DELETE p",
                document_id=document_id,
            )
            # Remove now-orphaned entities for this user.
            await session.run(
                """
                MATCH (e:Entity {user_id: $user_id})
                WHERE NOT (e)<-[:MENTIONS]-(:Paper)
                DETACH DELETE e
                """,
                user_id=user_id,
            )

    async def get_document_graph(
        self, *, user_id: str, document_id: str
    ) -> GraphResponse:
        driver = self._get_driver()
        async with driver.session() as session:
            ent_res = await session.run(
                """
                MATCH (p:Paper {id: $document_id, user_id: $user_id})-[:MENTIONS]->(e:Entity)
                RETURN e.key AS key, e.name AS name, e.type AS type
                """,
                document_id=document_id,
                user_id=user_id,
            )
            nodes = [
                GraphNode(id=r["key"], label=r["name"], type=r["type"])
                async for r in ent_res
            ]
            rel_res = await session.run(
                """
                MATCH (p:Paper {id: $document_id, user_id: $user_id})-[:MENTIONS]->(a:Entity)
                MATCH (p)-[:MENTIONS]->(b:Entity)
                MATCH (a)-[r:REL]->(b)
                RETURN a.key AS source, b.key AS target, r.label AS label
                """,
                document_id=document_id,
                user_id=user_id,
            )
            edges = [
                GraphEdge(source=r["source"], target=r["target"], label=r["label"])
                async for r in rel_res
            ]
        return GraphResponse(nodes=nodes, edges=edges)

    async def get_user_graph(self, *, user_id: str) -> GraphResponse:
        driver = self._get_driver()
        async with driver.session() as session:
            ent_res = await session.run(
                """
                MATCH (e:Entity {user_id: $user_id})
                OPTIONAL MATCH (e)<-[:MENTIONS]-(p:Paper)
                RETURN e.key AS key, e.name AS name, e.type AS type,
                       count(DISTINCT p) AS weight
                """,
                user_id=user_id,
            )
            nodes = [
                GraphNode(
                    id=r["key"], label=r["name"], type=r["type"], weight=r["weight"] or 1
                )
                async for r in ent_res
            ]
            rel_res = await session.run(
                """
                MATCH (a:Entity {user_id: $user_id})-[r:REL]->(b:Entity {user_id: $user_id})
                RETURN a.key AS source, b.key AS target, r.label AS label
                """,
                user_id=user_id,
            )
            edges = [
                GraphEdge(source=r["source"], target=r["target"], label=r["label"])
                async for r in rel_res
            ]
        return GraphResponse(nodes=nodes, edges=edges)


_store: Neo4jStore | None = None


def get_neo4j_store() -> Neo4jStore:
    global _store
    if _store is None:
        _store = Neo4jStore()
    return _store
