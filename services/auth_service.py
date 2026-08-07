import hashlib
import hmac
import os
import re
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from database.crud import UserRepository, log_history
from database.database import DB_PATH, init_db, session_scope
from database.models import User

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

    def register(self, username: str, password: str) -> tuple[bool, str]:
        username = str(username or "").strip()
        password = str(password or "")
        if not USERNAME_RE.match(username):
            return False, "Username must be 3–32 characters using letters, numbers, . _ or -."
        if len(password) < 4:
            return False, "Password must be at least 4 characters long."
        password_hash = hash_password(password)
        try:
            with session_scope(self.db_path) as session:
                obj = UserRepository(session).create(
                    username=username, password_hash=password_hash
                )
                log_history(
                    session,
                    "user_registered",
                    "user",
                    entity_id=obj.id,
                    details={"username": username},
                )
        except IntegrityError:
            return False, "That username is already taken."
        return True, f"Account for {obj.id} created."

    def authenticate(self, username: str, password: str) -> bool:
        username = str(username or "").strip()
        if not username:
            return False
        with session_scope(self.db_path) as session:
            user = UserRepository(session).by_username_case_insensitive(username)
            if user is None:
                return False
            return verify_password(str(password or ""), user.password_hash)

    def get_user(self, username: str) -> dict | None:
        with session_scope(self.db_path) as session:
            user = UserRepository(session).by_username_case_insensitive(
                str(username or "").strip()
            )
            if user is None:
                return None
            return {"id": user.id, "username": user.username, "created_at": user.created_at}

    def user_count(self) -> int:
        with session_scope(self.db_path) as session:
            return int(session.execute(select(func.count()).select_from(User)).scalar_one())

    def has_users(self) -> bool:
        return self.user_count() > 0
