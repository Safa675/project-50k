"""Create local team users; credentials never enter arguments or tool output."""
from __future__ import annotations
import argparse
import getpass
import json
import os
from pathlib import Path
import secrets
import sys
from pydantic import SecretStr
from p50k.product.auth import hash_password, normalized_email
from p50k.product.db import connect
from p50k.product.settings import Settings

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("create-user",))
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", choices=("viewer", "analyst", "admin"), default="viewer")
    parser.add_argument("--credential-file", type=Path)
    args = parser.parse_args()
    try:
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
