"""Throwaway e-mail providers (10-minute inboxes and the like) are refused at sign-up.

The list is disposable_email_blocklist.conf from
https://github.com/disposable-email-domains/disposable-email-domains (CC0), copied
into disposable_domains.txt; refresh it by downloading that file again.
"""

from functools import cache
from pathlib import Path

LIST = Path(__file__).with_name("disposable_domains.txt")


@cache
def _domains():
    lines = LIST.read_text(encoding="utf-8").splitlines()
    return frozenset(
        line.strip().lower() for line in lines if line.strip() and not line.startswith("#")
    )


def is_disposable(email):
    """True for an address at a listed domain or any subdomain of one."""
    domain = email.rpartition("@")[2].strip().lower().rstrip(".")
    parts = domain.split(".")
    return any(".".join(parts[i:]) in _domains() for i in range(len(parts) - 1))
