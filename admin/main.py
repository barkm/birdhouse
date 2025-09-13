import click

from firebase_admin import auth

from common.auth.firebase import initialize, set_authorization


@click.group()
def cli():
    initialize()
    pass


@cli.command()
@click.argument("uids", nargs=-1, required=True)
def authorize(uids: tuple[str, ...]):
    for uid in uids:
        set_authorization(uid, True)
        click.echo(f"User {uid} authorized")


@cli.command()
@click.argument("uids", nargs=-1, required=True)
def unauthorize(uids: tuple[str, ...]):
    for uid in uids:
        set_authorization(uid, False)
        click.echo(f"User {uid} unauthorized")


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
