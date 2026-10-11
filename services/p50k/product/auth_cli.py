"""Create local team users and set their profile photos; credentials never enter arguments or tool output."""
from __future__ import annotations
import argparse
import getpass
import json
import os
from pathlib import Path
import secrets
import sys
from pydantic import SecretStr
from p50k.product.auth import AVATAR_PATH_PATTERN, hash_password, normalized_email
from p50k.product.db import connect
from p50k.product.settings import Settings

def set_avatar(connection, email: str, avatar_path: str | None) -> str:
    """Set or clear one user's same-origin photo path and audit the change; returns the user id."""
    if avatar_path is not None and not AVATAR_PATH_PATTERN.fullmatch(avatar_path):
        raise ValueError("Avatar path must look like /avatars/<name>.jpg, .png or .webp")
    row = connection.execute("UPDATE auth.users SET avatar_path=%s WHERE email=%s RETURNING user_id",
        (avatar_path, normalized_email(email))).fetchone()
    if row is None:
        raise LookupError("No user has this email")
    connection.execute("INSERT INTO ops.audit_log(action,target_type,target_id) VALUES (%s,'USER',%s)",
        ("USER_AVATAR_SET" if avatar_path else "USER_AVATAR_CLEARED", str(row[0])))
    return str(row[0])

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("create-user", "set-avatar"))
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", choices=("viewer", "analyst", "admin"), default="viewer")
    parser.add_argument("--credential-file", type=Path)
    photo = parser.add_mutually_exclusive_group()
    photo.add_argument("--avatar-path", help="set-avatar: a file served by the web image, e.g. /avatars/name.jpg")
    photo.add_argument("--clear", action="store_true", help="set-avatar: remove the photo and show initials")
    args = parser.parse_args(argv)
    try:
        if args.command == "set-avatar":
            if args.avatar_path is None and not args.clear:
                raise ValueError("set-avatar needs --avatar-path or --clear")
            avatar_path = None if args.clear else args.avatar_path
            if avatar_path is not None and not AVATAR_PATH_PATTERN.fullmatch(avatar_path):
                raise ValueError("Avatar path must look like /avatars/<name>.jpg, .png or .webp")
            settings = Settings.from_env()
            if settings.db_user != "p50k_owner":
                raise ValueError("Account changes require the owner role")
            with connect(settings) as connection:
                set_avatar(connection, args.email, avatar_path)
            print("Profile photo updated." if avatar_path else "Profile photo cleared; initials are shown.")
            return 0
        if args.avatar_path is not None or args.clear:
            raise ValueError("Profile photo options belong to set-avatar")
        email, path = normalized_email(args.email), args.credential_file
        if path and ("secrets" not in path.parts or path.exists()):
            raise ValueError("Credential file must be new and inside secrets/")
        password = secrets.token_urlsafe(24) if path else getpass.getpass("Password: ") if sys.stdin.isatty() else sys.stdin.readline().rstrip("\r\n")
        settings = Settings.from_env()
        if settings.db_user != "p50k_owner":
            raise ValueError("Account provisioning requires the owner role")
        with connect(settings) as connection:
            user_id = connection.execute("INSERT INTO auth.users(email,password_hash,role) VALUES (%s,%s,%s) RETURNING user_id",
                (email, hash_password(SecretStr(password), settings.auth_pepper()), args.role)).fetchone()[0]
            connection.execute("INSERT INTO ops.audit_log(action,target_type,target_id) VALUES ('USER_CREATED','USER',%s)", (str(user_id),))
            if path:
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("x", encoding="utf-8", newline="\n") as stream:
                    os.chmod(path, 0o600)
                    stream.write(json.dumps({"email": email, "password": password}) + "\n")
        print("Local account created; credential values were not displayed.")
        return 0
    except Exception as error:
        print(json.dumps({"error_class": type(error).__name__}), file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
