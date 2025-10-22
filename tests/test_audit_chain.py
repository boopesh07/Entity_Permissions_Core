from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.database import session_scope
from app.models.audit_log import AuditLog
from app.models.entity import EntityStatus, EntityType
from app.schemas.assignment import RoleAssignmentCreate
from app.schemas.entity import EntityCreate, EntityUpdate
from app.schemas.role import RoleCreate
from app.services.audit import AuditService
from app.services.audit_verifier import AuditVerifier, AuditVerificationError
from app.services.entities import EntityService
from app.services.roles import RoleService


def test_audit_chain_sequences_and_hashes(client) -> None:
    with session_scope() as session:
        service = AuditService(session)
        service.record(action="unit.test.create", actor_id=None, entity_id=None, details={"step": 1})
        service.record(action="unit.test.update", actor_id=None, entity_id=None, details={"step": 2})

    with session_scope() as session:
        entries = session.execute(select(AuditLog).order_by(AuditLog.sequence)).scalars().all()
        assert len(entries) >= 2
        assert entries[0].sequence == 1
        assert entries[1].sequence == 2
        assert entries[1].previous_hash == entries[0].entry_hash

        verifier = AuditVerifier(session)
        result = verifier.verify()
        assert result.checked >= 2


def test_audit_chain_tampering_detected(client) -> None:
    event_id = uuid4()
    with session_scope() as session:
        service = AuditService(session)
        service.record(
            action="unit.test.tamper",
            actor_id=None,
            entity_id=None,
            details={"step": "tamper"},
            event_id=event_id,
        )

    with session_scope() as session:
        entry = session.execute(select(AuditLog).where(AuditLog.event_id == str(event_id))).scalar_one()
        entry.entry_hash = "deadbeef" * 8
        session.add(entry)

    with session_scope() as session:
        verifier = AuditVerifier(session)
        with pytest.raises(AuditVerificationError):
            verifier.verify()


def test_entity_and_role_actions_append_chained_audit_logs(client) -> None:
    actor_id = None
    with session_scope() as session:
        entity_service = EntityService(session)
        role_service = RoleService(session)

        entity = entity_service.create_entity(
            EntityCreate(
                name="Chain Test Issuer",
                type=EntityType.ISSUER,
                attributes={"region": "NA"},
                status=EntityStatus.ACTIVE,
            ),
            actor_id=actor_id,
        )
        entity_service.update(
            entity.id,
            EntityUpdate(name="Chain Test Issuer Updated", attributes={"region": "EU"}),
            actor_id=actor_id,
        )
        entity_service.archive(entity.id, actor_id=actor_id)

        role = role_service.create_role(
            RoleCreate(
                name="chain-role",
                description="",
                permissions=["document:upload"],
                scope_types=["issuer"],
            ),
            actor_id=actor_id,
        )
        principal_id = uuid4()
        assignment = role_service.assign_role(
            RoleAssignmentCreate(
                principal_id=principal_id,
                role_id=role.id,
                entity_id=entity.id,
                principal_type="user",
            ),
            actor_id=actor_id,
        )
        role_service.revoke_assignment(assignment.id, actor_id=actor_id)

    with session_scope() as session:
        entries = session.execute(select(AuditLog).order_by(AuditLog.sequence)).scalars().all()
        assert len(entries) >= 6
        for index, entry in enumerate(entries):
            if index == 0:
                assert entry.previous_hash == AuditService._GENESIS_HASH
            else:
                assert entry.previous_hash == entries[index - 1].entry_hash

        verifier = AuditVerifier(session)
        result = verifier.verify()
        assert result.checked == len(entries)


def test_audit_chain_reordering_detected(client) -> None:
    with session_scope() as session:
        service = AuditService(session)
        service.record(action="order.test.one", actor_id=None, entity_id=None, details={})
        second = service.record(action="order.test.two", actor_id=None, entity_id=None, details={})
        second_id = second.id

    with session_scope() as session:
        entry = session.get(AuditLog, second_id)
        entry.previous_hash = AuditService._GENESIS_HASH
        session.add(entry)

    with session_scope() as session:
        verifier = AuditVerifier(session)
        with pytest.raises(AuditVerificationError):
            verifier.verify()


def test_audit_verifier_replay_window(client) -> None:
    with session_scope() as session:
        service = AuditService(session)
        service.record(action="replay.one", actor_id=None, entity_id=None, details={})
        service.record(action="replay.two", actor_id=None, entity_id=None, details={})
        service.record(action="replay.three", actor_id=None, entity_id=None, details={})

    with session_scope() as session:
        verifier = AuditVerifier(session)
        result = verifier.verify(start_sequence=2)
        assert result.start_sequence == 2
        assert result.checked == 2
