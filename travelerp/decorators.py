"""
Role-Based Access Control (RBAC) Bridge
Consolidated with core.decorators enterprise RBAC engine.
Maintains backward compatibility for legacy imports.
"""
from core.decorators import (
    require_staff_role,
    require_staff_capability,
    require_financial_approval,
    has_staff_role,
    has_staff_capability,
    get_user_effective_roles,
    CAPABILITY_ROLE_MAP,
    GROUP_ROLE_MAP,
)

# Canonical alias for backwards compatibility
role_required = require_staff_role

__all__ = [
    'role_required',
    'require_staff_role',
    'require_staff_capability',
    'require_financial_approval',
    'has_staff_role',
    'has_staff_capability',
    'get_user_effective_roles',
    'CAPABILITY_ROLE_MAP',
    'GROUP_ROLE_MAP',
]
