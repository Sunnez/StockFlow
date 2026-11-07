from enum import Enum


class OrganizationRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    VIEWER = "viewer"


ROLE_LEVEL = {
    OrganizationRole.OWNER: 4,
    OrganizationRole.ADMIN: 3,
    OrganizationRole.MANAGER: 2,
    OrganizationRole.VIEWER: 1,
}