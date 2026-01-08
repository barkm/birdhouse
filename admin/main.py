import click

from firebase_admin import auth

from common.auth.firebase import Role, initialize, set_role, get_role


@click.group()
def cli():
    initialize()
    pass


@cli.command()
@click.argument("uids", nargs=-1, required=True)
@click.option(
    "--role",
    type=click.Choice([role.value for role in Role]),
    default=Role.USER.value,
    help="Role to assign",
)
def authorize(uids: tuple[str, ...], role: str):
    for uid in uids:
        set_role(uid, Role(role))
        click.echo(
            click.style(
                f"User {uid} authorized as {role}", fg=_get_role_color(Role(role))
            )
        )


@cli.command()
@click.argument("uids", nargs=-1, required=True)
def unauthorize(uids: tuple[str, ...]):
    for uid in uids:
        set_role(uid, None)
        click.echo(click.style(f"User {uid} unauthorized", fg=_get_role_color(None)))


@cli.command()
def list():
    page = auth.list_users()
    click.echo(click.style("UID \t\t\t\t Role \t Email", bold=True))
    while page:
        for u in page.users:
            role = get_role(u.custom_claims or {})
            click.echo(
                click.style(f"{u.uid} \t {role} \t {u.email}", fg=_get_role_color(role))
            )
        page = page.get_next_page()


def _get_role_color(role: Role | None) -> str:
    if role == Role.ADMIN:
        return "green"
    elif role == Role.USER:
        return "blue"
    else:
        return "red"


if __name__ == "__main__":
    cli()
