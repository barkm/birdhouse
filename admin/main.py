import click

from firebase_admin import auth

from common.auth.firebase import initialize


@click.group()
def cli():
    initialize()
    pass


@cli.command()
@click.argument("uids", nargs=-1, required=True)
def authorize(uids: tuple[str, ...]):
    for uid in uids:
        _set_authorization(uid, True)


@cli.command()
@click.argument("uids", nargs=-1, required=True)
def unauthorize(uids: tuple[str, ...]):
    for uid in uids:
        _set_authorization(uid, False)


def _set_authorization(uid: str, authorized: bool):
    user = auth.get_user(uid)
    claims = user.custom_claims or {}
    claims["authorized"] = authorized
    auth.set_custom_user_claims(uid, claims)
    status = "authorized" if authorized else "unauthorized"
    click.echo(f"User {uid} {status}")


@cli.command()
def list():
    page = auth.list_users()
    click.echo(click.style("UID \t\t\t\t Authorized \t Email", bold=True))
    while page:
        for u in page.users:
            authorized = (
                u.custom_claims.get("authorized", False) if u.custom_claims else False
            )
            click.echo(f"{u.uid} \t {authorized} \t\t {u.email}")
        page = page.get_next_page()


if __name__ == "__main__":
    cli()
