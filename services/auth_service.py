import hashlib
import hmac
import os
import re
from contextlib import contextmanager
from pathlib import Path

from database.database import DB_PATH, get_connection, init_db

HASH_ALGO = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 200_000
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")


def hash_password(password: str, iterations: int = PBKDF2_ITERATIONS) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", str(password).encode("utf-8"), salt, iterations
    )
    return f"{HASH_ALGO}${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_hex, digest_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
        digest_expected = bytes.fromhex(digest_hex)
    except (ValueError, AttributeError):
        return False
    if algo != HASH_ALGO:
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", str(password).encode("utf-8"), salt, int(iterations)
    )
    return hmac.compare_digest(digest, digest_expected)


class AuthService:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        init_db(self.db_path)

    @contextmanager
    def _connection(self):
        conn = get_connection(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def register(self, username: str, password: str) -> tuple[bool, str]:
        username = str(username or "").strip()
        password = str(password or "")
        if not USERNAME_RE.match(username):
            return False, "Username must be 3–32 characters using letters, numbers, . _ or -."
        if len(password) < 4:
            return False, "Password must be at least 4 characters long."
        password_hash = hash_password(password)
        with self._connection() as conn:
            try:
                cursor = conn.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, password_hash),
                )
                conn.commit()
            except Exception:
                return False, "That username is already taken."
        return True, f"Account for {cursor.lastrowid} created."

    def authenticate(self, username: str, password: str) -> bool:
        username = str(username or "").strip()
        if not username:
            return False
        with self._connection() as conn:
            row = conn.execute(
                "SELECT password_hash FROM users WHERE username = ? COLLATE NOCASE",
                (username,),
            ).fetchone()
        if row is None:
            return False
        return verify_password(str(password or ""), row["password_hash"])

    def get_user(self, username: str) -> dict | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT id, username, created_at FROM users "
                "WHERE username = ? COLLATE NOCASE",
                (str(username or "").strip(),),
            ).fetchone()
        return dict(row) if row else None

    def user_count(self) -> int:
        with self._connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()
        return int(row["n"])

    def has_users(self) -> bool:
        return self.user_count() > 0
