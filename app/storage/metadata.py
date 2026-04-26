from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import json
from pathlib import Path
from typing import Iterator

from sqlalchemy import DateTime, Integer, String, Text, create_engine, select, tuple_
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.core.models import Chunk, Collection, RetrievalRunRecord, SourceDocument


class Base(DeclarativeBase):
    pass


def _to_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _from_json(payload: str | None, default):
    if not payload:
        return default
    return json.loads(payload)


class CollectionORM(Base):
    __tablename__ = "collections"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    domain: Mapped[str] = mapped_column(String(128), default="general")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")


class SourceDocumentORM(Base):
    __tablename__ = "source_documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_uri: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_text_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")


class ChunkORM(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    section_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parent_span: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")


class RetrievalRunORM(Base):
    __tablename__ = "retrieval_runs"

    query_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    collection_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    candidate_count: Mapped[int] = mapped_column(Integer, default=0)
    merged_count: Mapped[int] = mapped_column(Integer, default=0)
    reranked_count: Mapped[int] = mapped_column(Integer, default=0)
    kept_evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    token_estimate: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    strategy_config_json: Mapped[str] = mapped_column(Text, default="{}")
    evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    trace_steps_json: Mapped[str] = mapped_column(Text, default="[]")
    drop_reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    score_snapshots_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SQLiteMetadataStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{self.db_path}", future=True)
        self._session_factory = sessionmaker(bind=self.engine, future=True)

    def init_db(self) -> None:
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def upsert_collection(self, item: Collection) -> None:
        with self.session() as session:
            existing = session.get(CollectionORM, item.id)
            if existing is None:
                session.add(
                    CollectionORM(
                        id=item.id,
                        name=item.name,
                        description=item.description,
                        domain=item.domain,
                        created_at=item.created_at,
                        updated_at=item.updated_at,
                        metadata_json=_to_json(item.metadata),
                    )
                )
            else:
                existing.name = item.name
                existing.description = item.description
                existing.domain = item.domain
                existing.updated_at = item.updated_at
                existing.metadata_json = _to_json(item.metadata)

    def get_collection(self, collection_id: str) -> Collection | None:
        with self.session() as session:
            row = session.get(CollectionORM, collection_id)
            if row is None:
                return None
            return Collection(
                id=row.id,
                name=row.name,
                description=row.description,
                domain=row.domain,
                created_at=row.created_at,
                updated_at=row.updated_at,
                metadata=_from_json(row.metadata_json, {}),
            )

    def list_collections(self) -> list[Collection]:
        with self.session() as session:
            rows = session.execute(select(CollectionORM).order_by(CollectionORM.created_at.desc())).scalars().all()
            return [
                Collection(
                    id=row.id,
                    name=row.name,
                    description=row.description,
                    domain=row.domain,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    metadata=_from_json(row.metadata_json, {}),
                )
                for row in rows
            ]

    def upsert_source_document(self, item: SourceDocument) -> None:
        with self.session() as session:
            existing = session.get(SourceDocumentORM, item.id)
            if existing is None:
                session.add(
                    SourceDocumentORM(
                        id=item.id,
                        collection_id=item.collection_id,
                        title=item.title,
                        source_uri=item.source_uri,
                        source_type=item.source_type,
                        checksum=item.checksum,
                        published_at=item.published_at,
                        raw_text_path=item.raw_text_path,
                        ingested_at=item.ingested_at,
                        metadata_json=_to_json(item.metadata),
                    )
                )
            else:
                existing.title = item.title
                existing.source_uri = item.source_uri
                existing.source_type = item.source_type
                existing.checksum = item.checksum
                existing.published_at = item.published_at
                existing.raw_text_path = item.raw_text_path
                existing.ingested_at = item.ingested_at
                existing.metadata_json = _to_json(item.metadata)

    def list_documents(self, collection_id: str) -> list[SourceDocument]:
        with self.session() as session:
            rows = (
                session.execute(
                    select(SourceDocumentORM)
                    .where(SourceDocumentORM.collection_id == collection_id)
                    .order_by(SourceDocumentORM.ingested_at.desc())
                )
                .scalars()
                .all()
            )
            return [
                SourceDocument(
                    id=row.id,
                    collection_id=row.collection_id,
                    title=row.title,
                    source_uri=row.source_uri,
                    source_type=row.source_type,
                    checksum=row.checksum,
                    published_at=row.published_at,
                    ingested_at=row.ingested_at,
                    raw_text_path=row.raw_text_path,
                    metadata=_from_json(row.metadata_json, {}),
                )
                for row in rows
            ]

    def list_chunks(self, collection_id: str) -> list[Chunk]:
        with self.session() as session:
            rows = (
                session.execute(
                    select(ChunkORM, SourceDocumentORM)
                    .join(SourceDocumentORM, ChunkORM.document_id == SourceDocumentORM.id)
                    .where(SourceDocumentORM.collection_id == collection_id)
                    .order_by(SourceDocumentORM.ingested_at.desc(), ChunkORM.chunk_index.asc())
                )
                .all()
            )
            return [
                Chunk(
                    id=chunk_row.id,
                    document_id=chunk_row.document_id,
                    chunk_index=chunk_row.chunk_index,
                    text=chunk_row.text,
                    token_count=chunk_row.token_count,
                    section_title=chunk_row.section_title,
                    parent_span=chunk_row.parent_span,
                    metadata=_from_json(chunk_row.metadata_json, {}),
                )
                for chunk_row, _document_row in rows
            ]

    def get_chunk_records_by_ids(self, chunk_ids: list[str]) -> list[dict]:
        if not chunk_ids:
            return []

        with self.session() as session:
            rows = (
                session.execute(
                    select(ChunkORM, SourceDocumentORM)
                    .join(SourceDocumentORM, ChunkORM.document_id == SourceDocumentORM.id)
                    .where(ChunkORM.id.in_(chunk_ids))
                )
                .all()
            )

            record_map = {
                chunk_row.id: {
                    "chunk": Chunk(
                        id=chunk_row.id,
                        document_id=chunk_row.document_id,
                        chunk_index=chunk_row.chunk_index,
                        text=chunk_row.text,
                        token_count=chunk_row.token_count,
                        section_title=chunk_row.section_title,
                        parent_span=chunk_row.parent_span,
                        metadata=_from_json(chunk_row.metadata_json, {}),
                    ),
                    "document": SourceDocument(
                        id=document_row.id,
                        collection_id=document_row.collection_id,
                        title=document_row.title,
                        source_uri=document_row.source_uri,
                        source_type=document_row.source_type,
                        checksum=document_row.checksum,
                        published_at=document_row.published_at,
                        ingested_at=document_row.ingested_at,
                        raw_text_path=document_row.raw_text_path,
                        metadata=_from_json(document_row.metadata_json, {}),
                    ),
                }
                for chunk_row, document_row in rows
            }
            return [record_map[chunk_id] for chunk_id in chunk_ids if chunk_id in record_map]

    def get_chunk_records_by_document_indexes(
        self,
        collection_id: str,
        document_indexes: dict[str, set[int]],
    ) -> list[dict]:
        pairs = [
            (document_id, chunk_index)
            for document_id, chunk_indexes in document_indexes.items()
            for chunk_index in chunk_indexes
        ]
        if not pairs:
            return []

        with self.session() as session:
            rows = (
                session.execute(
                    select(ChunkORM, SourceDocumentORM)
                    .join(SourceDocumentORM, ChunkORM.document_id == SourceDocumentORM.id)
                    .where(SourceDocumentORM.collection_id == collection_id)
                    .where(tuple_(ChunkORM.document_id, ChunkORM.chunk_index).in_(pairs))
                )
                .all()
            )

            return [
                {
                    "chunk": Chunk(
                        id=chunk_row.id,
                        document_id=chunk_row.document_id,
                        chunk_index=chunk_row.chunk_index,
                        text=chunk_row.text,
                        token_count=chunk_row.token_count,
                        section_title=chunk_row.section_title,
                        parent_span=chunk_row.parent_span,
                        metadata=_from_json(chunk_row.metadata_json, {}),
                    ),
                    "document": SourceDocument(
                        id=document_row.id,
                        collection_id=document_row.collection_id,
                        title=document_row.title,
                        source_uri=document_row.source_uri,
                        source_type=document_row.source_type,
                        checksum=document_row.checksum,
                        published_at=document_row.published_at,
                        ingested_at=document_row.ingested_at,
                        raw_text_path=document_row.raw_text_path,
                        metadata=_from_json(document_row.metadata_json, {}),
                    ),
                }
                for chunk_row, document_row in rows
            ]

    def checksum_exists(self, checksum: str, collection_id: str | None = None) -> bool:
        with self.session() as session:
            stmt = select(SourceDocumentORM.id).where(SourceDocumentORM.checksum == checksum)
            if collection_id is not None:
                stmt = stmt.where(SourceDocumentORM.collection_id == collection_id)
            return session.execute(stmt.limit(1)).first() is not None

    def upsert_chunks(self, items: list[Chunk]) -> None:
        with self.session() as session:
            for item in items:
                existing = session.get(ChunkORM, item.id)
                if existing is None:
                    session.add(
                        ChunkORM(
                            id=item.id,
                            document_id=item.document_id,
                            chunk_index=item.chunk_index,
                            text=item.text,
                            token_count=item.token_count,
                            section_title=item.section_title,
                            parent_span=item.parent_span,
                            metadata_json=_to_json(item.metadata),
                        )
                    )
                else:
                    existing.document_id = item.document_id
                    existing.chunk_index = item.chunk_index
                    existing.text = item.text
                    existing.token_count = item.token_count
                    existing.section_title = item.section_title
                    existing.parent_span = item.parent_span
                    existing.metadata_json = _to_json(item.metadata)

    def log_retrieval_run(self, item: RetrievalRunRecord) -> None:
        with self.session() as session:
            session.merge(
                RetrievalRunORM(
                    query_id=item.query_id,
                    query=item.query,
                    collection_id=item.collection_id,
                    candidate_count=item.candidate_count,
                    merged_count=item.merged_count,
                    reranked_count=item.reranked_count,
                    kept_evidence_count=item.kept_evidence_count,
                    token_estimate=item.token_estimate,
                    latency_ms=item.latency_ms,
                    strategy_config_json=_to_json(item.strategy_config),
                    evidence_ids_json=_to_json(item.evidence_ids),
                    trace_steps_json=_to_json(item.trace_steps),
                    drop_reasons_json=_to_json(item.drop_reasons),
                    score_snapshots_json=_to_json(item.score_snapshots),
                    created_at=item.created_at,
                )
            )
