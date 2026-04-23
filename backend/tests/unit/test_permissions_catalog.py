"""Permission katalog single-source-of-truth invariantlari."""
from app.core.permissions import ALL_PERMISSIONS, P, all_codenames


def test_all_permissions_unique():
    codes = all_codenames()
    assert len(codes) == len(set(codes)), "Codename lar takroriy"


def test_all_permissions_have_group():
    for perm in ALL_PERMISSIONS:
        assert perm.group, f"{perm.code} uchun group bo'sh"


def test_all_permissions_have_name():
    for perm in ALL_PERMISSIONS:
        assert perm.name, f"{perm.code} uchun name bo'sh"


def test_code_follows_convention():
    """Barcha codename'lar <group>:<action> format'ida."""
    for perm in ALL_PERMISSIONS:
        assert ":" in perm.code, f"{perm.code} ':' belgisi yo'q"


def test_p_class_has_admin_critical_perms():
    critical = [
        P.USER_READ,
        P.USER_CREATE,
        P.ROLE_READ,
        P.ROLE_UPDATE,
        P.PERMISSION_READ,
    ]
    for perm in critical:
        assert perm.code in all_codenames()
