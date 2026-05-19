"""Tests for content-addressed entity IDs (#247)."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from memoryhub_core.models.memory import MemoryNode
from memoryhub_core.services.embeddings import EmbeddingService
from memoryhub_core.services.entity import compute_entity_hash, find_or_create_entity


def test_compute_entity_hash_deterministic() -> None:
    """Same inputs produce same hash."""
    tenant_id = "test-tenant"
    owner_id = "user-123"
    name = "Alice"
    entity_type = "person"

    hash1 = compute_entity_hash(tenant_id, owner_id, name, entity_type)
    hash2 = compute_entity_hash(tenant_id, owner_id, name, entity_type)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex digest


def test_compute_entity_hash_case_insensitive() -> None:
    """'Alice' and 'alice' produce the same hash."""
    tenant_id = "test-tenant"
    owner_id = "user-123"
    entity_type = "person"

    hash_upper = compute_entity_hash(tenant_id, owner_id, "Alice", entity_type)
    hash_lower = compute_entity_hash(tenant_id, owner_id, "alice", entity_type)
    hash_mixed = compute_entity_hash(tenant_id, owner_id, "aLiCe", entity_type)

    assert hash_upper == hash_lower == hash_mixed


def test_compute_entity_hash_whitespace_normalized() -> None:
    """Leading/trailing whitespace is stripped."""
    tenant_id = "test-tenant"
    owner_id = "user-123"
    entity_type = "person"

    hash_clean = compute_entity_hash(tenant_id, owner_id, "Bob", entity_type)
    hash_padded = compute_entity_hash(tenant_id, owner_id, "  Bob  ", entity_type)

    assert hash_clean == hash_padded


def test_compute_entity_hash_different_types() -> None:
    """Different entity types produce different hashes."""
    tenant_id = "test-tenant"
    owner_id = "user-123"
    name = "Springfield"

    hash_location = compute_entity_hash(tenant_id, owner_id, name, "location")
    hash_org = compute_entity_hash(tenant_id, owner_id, name, "organization")

    assert hash_location != hash_org


def test_compute_entity_hash_different_owners() -> None:
    """Different owners produce different hashes."""
    tenant_id = "test-tenant"
    name = "Alice"
    entity_type = "person"

    hash_user1 = compute_entity_hash(tenant_id, "user-1", name, entity_type)
    hash_user2 = compute_entity_hash(tenant_id, "user-2", name, entity_type)

    assert hash_user1 != hash_user2


def test_compute_entity_hash_different_tenants() -> None:
    """Different tenants produce different hashes."""
    owner_id = "user-123"
    name = "Alice"
    entity_type = "person"

    hash_tenant1 = compute_entity_hash("tenant-1", owner_id, name, entity_type)
    hash_tenant2 = compute_entity_hash("tenant-2", owner_id, name, entity_type)

    assert hash_tenant1 != hash_tenant2


@pytest.mark.asyncio
async def test_find_or_create_entity_uses_hash(
    async_session: AsyncSession,
    embedding_service: EmbeddingService,
) -> None:
    """Entity creation sets content_hash."""
    entity, was_created = await find_or_create_entity(
        name="Alice",
        entity_type="person",
        session=async_session,
        embedding_service=embedding_service,
        tenant_id="test-tenant",
        owner_id="user-123",
    )

    assert was_created is True
    assert entity.content_hash is not None
    assert len(entity.content_hash) == 64

    # Verify the hash is stored in the database
    stmt = select(MemoryNode).where(MemoryNode.id == entity.id)
    result = await async_session.execute(stmt)
    node = result.scalar_one()
    assert node.content_hash == entity.content_hash


@pytest.mark.asyncio
async def test_find_or_create_entity_dedup_via_hash(
    async_session: AsyncSession,
    embedding_service: EmbeddingService,
) -> None:
    """Creating same entity twice returns existing one via hash."""
    # Create first entity
    entity1, was_created1 = await find_or_create_entity(
        name="Alice",
        entity_type="person",
        session=async_session,
        embedding_service=embedding_service,
        tenant_id="test-tenant",
        owner_id="user-123",
    )
    assert was_created1 is True
    hash1 = entity1.content_hash

    # Try to create same entity again
    entity2, was_created2 = await find_or_create_entity(
        name="Alice",
        entity_type="person",
        session=async_session,
        embedding_service=embedding_service,
        tenant_id="test-tenant",
        owner_id="user-123",
    )

    assert was_created2 is False
    assert entity2.id == entity1.id
    assert entity2.content_hash == hash1


@pytest.mark.asyncio
async def test_find_or_create_entity_dedup_case_insensitive(
    async_session: AsyncSession,
    embedding_service: EmbeddingService,
) -> None:
    """Creating 'Alice' then 'alice' returns the same entity."""
    # Create with capitalized name
    entity1, was_created1 = await find_or_create_entity(
        name="Alice",
        entity_type="person",
        session=async_session,
        embedding_service=embedding_service,
        tenant_id="test-tenant",
        owner_id="user-123",
    )
    assert was_created1 is True

    # Try to create with lowercase name
    entity2, was_created2 = await find_or_create_entity(
        name="alice",
        entity_type="person",
        session=async_session,
        embedding_service=embedding_service,
        tenant_id="test-tenant",
        owner_id="user-123",
    )

    assert was_created2 is False
    assert entity2.id == entity1.id
    assert entity2.content_hash == entity1.content_hash


@pytest.mark.asyncio
async def test_find_or_create_entity_different_types_separate(
    async_session: AsyncSession,
    embedding_service: EmbeddingService,
) -> None:
    """Same name but different entity types create separate entities."""
    # Create a location named "Springfield"
    entity_location, was_created1 = await find_or_create_entity(
        name="Springfield",
        entity_type="location",
        session=async_session,
        embedding_service=embedding_service,
        tenant_id="test-tenant",
        owner_id="user-123",
    )
    assert was_created1 is True

    # Create an organization named "Springfield"
    entity_org, was_created2 = await find_or_create_entity(
        name="Springfield",
        entity_type="organization",
        session=async_session,
        embedding_service=embedding_service,
        tenant_id="test-tenant",
        owner_id="user-123",
    )

    assert was_created2 is True
    assert entity_org.id != entity_location.id
    assert entity_org.content_hash != entity_location.content_hash
