import logging
from sqlalchemy.orm import Session
from .models.auth_models import Role, Permission, RolePermission

logger = logging.getLogger(__name__)

PERMISSIONS = [
    ("manage_users", "Can manage users"),
    ("manage_roles", "Can manage roles and permissions"),
    ("manage_billing", "Can manage subscription and billing"),
    ("manage_system_settings", "Can manage global system settings"),
    ("view_analytics", "Can view system analytics"),
    ("manage_campaigns", "Can create and manage campaigns"),
    ("manage_companies", "Can manage companies"),
    ("manage_recruiters", "Can manage recruiters"),
    ("export_data", "Can export data"),
    ("view_data", "Can view data"),
]

ROLES = [
    ("superadmin", "Full platform access"),
    ("admin", "Administrative access"),
    ("manager", "Team management access"),
    ("recruiter", "Recruiter access"),
    ("user", "Standard user access"),
    ("readonly", "Read-only access"),
]

ROLE_PERMISSIONS_MAP = {
    "superadmin": [p[0] for p in PERMISSIONS],
    "admin": ["manage_users", "view_analytics", "manage_campaigns", "manage_companies", "manage_recruiters", "export_data", "view_data"],
    "manager": ["view_analytics", "manage_campaigns", "manage_companies", "manage_recruiters", "view_data"],
    "recruiter": ["manage_companies", "manage_recruiters", "view_data"],
    "user": ["view_data"],
    "readonly": ["view_data"]
}

def seed_roles_and_permissions(db: Session):
    logger.info("Seeding roles and permissions...")
    
    # Ensure permissions exist
    perm_map = {}
    for p_name, p_desc in PERMISSIONS:
        perm = db.query(Permission).filter(Permission.name == p_name).first()
        if not perm:
            perm = Permission(name=p_name, description=p_desc)
            db.add(perm)
            db.commit()
            db.refresh(perm)
        perm_map[p_name] = perm.id
        
    # Ensure roles exist
    for r_name, r_desc in ROLES:
        role = db.query(Role).filter(Role.name == r_name).first()
        if not role:
            role = Role(name=r_name, description=r_desc)
            db.add(role)
            db.commit()
            db.refresh(role)
            
        # Assign permissions
        allowed_perms = ROLE_PERMISSIONS_MAP.get(r_name, [])
        for p_name in allowed_perms:
            p_id = perm_map[p_name]
            mapping = db.query(RolePermission).filter(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == p_id
            ).first()
            if not mapping:
                db.add(RolePermission(role_id=role.id, permission_id=p_id))
    
    db.commit()
    logger.info("Roles and permissions seeded successfully.")
