"""Local operator provisioning and recovery for staff accounts."""

import argparse
from getpass import getpass

from sqlalchemy import text

from app.database import get_engine
from app.editorial_auth import create_user, hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Create, reset, or disable a publication-scoped editorial account")
    parser.add_argument("action", choices=("create", "reset-password", "disable", "grant-publisher", "revoke-publisher"))
    parser.add_argument("--username", required=True)
    parser.add_argument("--organization-slug", default="whats-on-my-ballot")
    parser.add_argument("--publication-slug", default="copperas-cove")
    args = parser.parse_args()
    password = None
    if args.action in {"create", "reset-password"}:
        password = getpass("New passphrase (15+ characters): ")
        if password != getpass("Repeat passphrase: "):
            raise SystemExit("Passphrases did not match. No changes made.")
        try:
            password_hash = hash_password(password)
        except ValueError as error:
            raise SystemExit(str(error)) from error
    with get_engine().begin() as connection:
        publication = connection.execute(text(
            "SELECT p.id FROM publications p JOIN organizations o ON o.id=p.organization_id WHERE p.slug=:p AND o.slug=:o"
        ), {"p": args.publication_slug, "o": args.organization_slug}).scalar_one_or_none()
        if publication is None:
            raise SystemExit("Publication not found. Run pilot setup first.")
        user = connection.execute(text("SELECT id FROM editorial_users WHERE username=:u AND publication_id=:p FOR UPDATE"),
                                  {"u": args.username, "p": publication}).scalar_one_or_none()
        if args.action == "create":
            if user is not None:
                raise SystemExit("Staff account already exists; use reset-password if needed.")
            create_user(connection, publication, args.username, password)
        else:
            if user is None:
                raise SystemExit("Staff account was not found in this publication.")
            if args.action == "reset-password":
                connection.execute(text("UPDATE editorial_users SET password_hash=:h,failed_logins=0,locked_until=NULL WHERE id=:id"),
                                   {"h": password_hash, "id": user})
            elif args.action == "disable":
                connection.execute(text("UPDATE editorial_users SET active=FALSE WHERE id=:id"), {"id": user})
            else:
                connection.execute(text("UPDATE editorial_users SET can_publish=:allowed WHERE id=:id"),
                                   {"id": user, "allowed": args.action == "grant-publisher"})
            connection.execute(text("DELETE FROM editorial_sessions WHERE user_id=:id"), {"id": user})
    print("Staff account updated. Existing reviews remain in the audit history.")


if __name__ == "__main__":
    main()
