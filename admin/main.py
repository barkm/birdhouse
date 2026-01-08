import click

from firebase_admin import auth

from common.auth.firebase import Role, initialize, set_role, get_role


@click.group()
def cli():
    initialize()
    pass


@cli.command()
@click.argument("uids", nargs=-1, required=True)
def authorize(uids: tuple[str, ...]):
    for uid in uids:
        set_role(uid, Role.USER)
        click.echo(f"User {uid} authorized")


@cli.command()
@click.argument("uids", nargs=-1, required=True)
def unauthorize(uids: tuple[str, ...]):
    for uid in uids:
        set_role(uid, None)
        click.echo(f"User {uid} unauthorized")


@cli.command()
def list():
    page = auth.list_users()
    click.echo(click.style("UID \t\t\t\t Role \t Email", bold=True))
    while page:
        for u in page.users:
            role = get_role(u.custom_claims or {})
            click.echo(f"{u.uid} \t {role} \t {u.email}")
        page = page.get_next_page()


if __name__ == "__main__":
    cli()
