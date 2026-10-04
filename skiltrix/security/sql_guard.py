"""
SkilTrix Universal Security Firewall - SQL Security Guard
Enforces database isolation, prevents database escaping (ATTACH DATABASE, VACUUM INTO),
blocks file read/write operations via SQL functions, and stops system table tampering.
"""

import re
from typing import Dict, Any, List, Optional

from .policies import (
    SecurityPolicyViolation,
    RULE_SQL_CONFINEMENT,
    RULE_DANGEROUS_FILESYSTEM,
)

RE_ATTACH = re.compile(r'\bATTACH(?:\s+DATABASE)?\b', re.IGNORECASE)
RE_DETACH = re.compile(r'\bDETACH(?:\s+DATABASE)?\b', re.IGNORECASE)
RE_VACUUM_INTO = re.compile(r'\bVACUUM\s+INTO\b', re.IGNORECASE)
RE_LOAD_EXTENSION = re.compile(r'\b(?:load_extension|sqlite3_load_extension)\b', re.IGNORECASE)
RE_LOAD_FILE = re.compile(r'\bLOAD_FILE\b', re.IGNORECASE)
RE_INTO_OUTFILE = re.compile(r'\bINTO\s+(?:OUTFILE|DUMPFILE)\b', re.IGNORECASE)
RE_WRITABLE_SCHEMA = re.compile(r'\bPRAGMA\s+writable_schema\b', re.IGNORECASE)
RE_SYSTEM_CATALOG_WRITE = re.compile(r'\b(?:INSERT|UPDATE|DELETE|DROP)\s+.*?\b(?:sqlite_master|sqlite_schema)\b', re.IGNORECASE)


class SqlSecurityGuard:
    """Validates SQL scripts to guarantee query isolation to the active project database."""

    @classmethod
    def validate_statement(cls, stmt: str) -> None:
        """
        Inspects an individual SQL statement.
        Raises SecurityPolicyViolation if statement attempts database escape or tampering.
        """
        clean = stmt.strip()
        if not clean:
            return

        # 1. ATTACH DATABASE escape
        if RE_ATTACH.search(clean):
            raise SecurityPolicyViolation(
                message="ATTACH DATABASE is blocked; queries must remain confined to the selected project database.",
                rule_triggered=RULE_SQL_CONFINEMENT,
                language="sql",
                entry_point="sql_guard",
            )

        # 2. VACUUM INTO disk write
        if RE_VACUUM_INTO.search(clean):
            raise SecurityPolicyViolation(
                message="VACUUM INTO arbitrary filesystem paths is forbidden.",
                rule_triggered=RULE_DANGEROUS_FILESYSTEM,
                language="sql",
                entry_point="sql_guard",
            )

        # 3. Dynamic extension loading
        if RE_LOAD_EXTENSION.search(clean):
            raise SecurityPolicyViolation(
                message="Loading native SQLite database extensions is blocked by security policy.",
                rule_triggered=RULE_SQL_CONFINEMENT,
                language="sql",
                entry_point="sql_guard",
            )

        # 4. Host file read/dump primitives (MySQL / Postgres / SQLite dialect attempts)
        if RE_LOAD_FILE.search(clean) or RE_INTO_OUTFILE.search(clean):
            raise SecurityPolicyViolation(
                message="Direct filesystem reading/writing through SQL primitives is forbidden.",
                rule_triggered=RULE_DANGEROUS_FILESYSTEM,
                language="sql",
                entry_point="sql_guard",
            )

        # 5. Schema hacking PRAGMAs
        if RE_WRITABLE_SCHEMA.search(clean):
            raise SecurityPolicyViolation(
                message="PRAGMA writable_schema tampering is forbidden.",
                rule_triggered=RULE_SQL_CONFINEMENT,
                language="sql",
                entry_point="sql_guard",
            )

        # 6. Direct writes to sqlite_master / sqlite_schema
        if RE_SYSTEM_CATALOG_WRITE.search(clean):
            raise SecurityPolicyViolation(
                message="Direct modification of internal catalog tables (sqlite_master) is forbidden.",
                rule_triggered=RULE_SQL_CONFINEMENT,
                language="sql",
                entry_point="sql_guard",
            )

    @classmethod
    def validate_script(cls, script: str) -> None:
        """Splits and validates all statements within a SQL script."""
        # Split on semicolons while respecting quotes
        parts = []
        cur = []
        in_squote = False
        in_dquote = False

        for char in script:
            if char == "'" and not in_dquote:
                in_squote = not in_squote
            elif char == '"' and not in_squote:
                in_dquote = not in_dquote
            elif char == ';' and not in_squote and not in_dquote:
                parts.append("".join(cur))
                cur = []
                continue
            cur.append(char)
        if cur:
            parts.append("".join(cur))

        for part in parts:
            cls.validate_statement(part)

