"""Permission action constants for the platform."""

from __future__ import annotations

from typing import List

# Document permissions (existing)
DOCUMENT_UPLOAD = "document:upload"
DOCUMENT_VERIFY = "document:verify"
DOCUMENT_DOWNLOAD = "document:download"
DOCUMENT_ARCHIVE = "document:archive"

# Property management permissions
PROPERTY_CREATE = "property:create"
PROPERTY_VIEW = "property:view"
PROPERTY_UPDATE = "property:update"
PROPERTY_APPROVE = "property:approve"
PROPERTY_TOKENIZE = "property:tokenize"

# Token operation permissions
TOKEN_VIEW = "token:view"
TOKEN_TRADE = "token:trade"
TOKEN_TRANSFER = "token:transfer"
TOKEN_MINT = "token:mint"

# User management permissions
USER_ONBOARD = "user:onboard"
USER_APPROVE = "user:approve"
USER_MANAGE = "user:manage"


def get_all_permissions() -> List[str]:
    """Return list of all permission actions."""
    return [
        # Document permissions
        DOCUMENT_UPLOAD,
        DOCUMENT_VERIFY,
        DOCUMENT_DOWNLOAD,
        DOCUMENT_ARCHIVE,
        # Property permissions
        PROPERTY_CREATE,
        PROPERTY_VIEW,
        PROPERTY_UPDATE,
        PROPERTY_APPROVE,
        PROPERTY_TOKENIZE,
        # Token permissions
        TOKEN_VIEW,
        TOKEN_TRADE,
        TOKEN_TRANSFER,
        TOKEN_MINT,
        # User permissions
        USER_ONBOARD,
        USER_APPROVE,
        USER_MANAGE,
    ]


def get_agent_permissions() -> List[str]:
    """Return permissions for Agent role."""
    return [
        DOCUMENT_UPLOAD,
        DOCUMENT_VERIFY,
        DOCUMENT_DOWNLOAD,
        DOCUMENT_ARCHIVE,
        PROPERTY_CREATE,
        PROPERTY_VIEW,
        PROPERTY_UPDATE,
        PROPERTY_APPROVE,
        PROPERTY_TOKENIZE,
        TOKEN_VIEW,
        USER_ONBOARD,
        USER_APPROVE,
        USER_MANAGE,
    ]


def get_property_owner_permissions() -> List[str]:
    """Return permissions for Property Owner role."""
    return [
        DOCUMENT_UPLOAD,
        DOCUMENT_DOWNLOAD,
        PROPERTY_CREATE,
        PROPERTY_VIEW,
        PROPERTY_UPDATE,
        TOKEN_VIEW,
    ]


def get_investor_pending_permissions() -> List[str]:
    """Return permissions for Investor (Pending) role."""
    return [
        DOCUMENT_UPLOAD,
        DOCUMENT_DOWNLOAD,
        PROPERTY_VIEW,
        TOKEN_VIEW,
    ]


def get_investor_active_permissions() -> List[str]:
    """Return permissions for Investor (Active) role."""
    return [
        DOCUMENT_UPLOAD,
        DOCUMENT_DOWNLOAD,
        PROPERTY_VIEW,
        TOKEN_VIEW,
        TOKEN_TRADE,
    ]


