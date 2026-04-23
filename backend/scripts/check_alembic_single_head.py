"""CI uchun: alembic yagona head borligini tekshiradi.

Ishlatish:
    python backend/scripts/check_alembic_single_head.py

Agar 1 tadan ortiq head bo'lsa, exit code 1 qaytaradi.
"""
import os
import re
import sys

VERSIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "app",
    "db",
    "migrations",
    "versions",
)


def main() -> int:
    revs: set[str] = set()
    downs: set[str] = set()
    for fname in os.listdir(VERSIONS_DIR):
        if not fname.endswith(".py") or fname.startswith("__"):
            continue
        with open(os.path.join(VERSIONS_DIR, fname), encoding="utf-8") as f:
            content = f.read()
        rev_m = re.search(r"^revision[^=]*=\s*[\"']([a-zA-Z0-9]+)[\"']", content, re.M)
        if not rev_m:
            continue
        revs.add(rev_m.group(1))
        # down_revision bir nechta bo'lishi mumkin (tuple)
        for m in re.finditer(r"[\"']([a-f0-9]{10,})[\"']", content):
            if m.group(1) != rev_m.group(1):
                downs.add(m.group(1))

    heads = revs - downs
    if len(heads) > 1:
        print(f"FAIL: {len(heads)} ta alembic head topildi:")
        for h in sorted(heads):
            print(f"  - {h}")
        print(
            "Yechim: `alembic merge -m 'merge heads' <head1> <head2> ...` "
            "buyrug'i bilan merge migration yarating."
        )
        return 1

    head = heads.pop() if heads else "(topilmadi)"
    print(f"OK: yagona head {head}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
