from pathlib import Path
from subprocess import check_call
import getpass
import os

import click

@click.group()
def cli():
    pass

@cli.command()
@click.option("--name", required=True)
@click.option("--command", required=True)
@click.option("environment_variables", "--environment", multiple=True, default=[])
def install(name: str, command: str, environment_variables: list[str]):
    _write_service_file(name, command, environment_variables)
    _enable_service(name)
    _start_service(name)

@cli.command()
@click.option("--name", required=True)
def uninstall(name: str):
    _stop_service(name)
    _disable_service(name)
    _remove_service_file(name)
    

def _write_service_file(name: str, command: str, environment_variables: list[str]) -> None:
    file_path = _get_service_file_path(name)
    content = _get_service_file_content(command, environment_variables)
    if file_path.exists():
        raise FileExistsError(f"{name} is already configured at {file_path}")
    file_path.write_text(content)


def _remove_service_file(name: str) -> None:
    _get_service_file_path(name).unlink()


def _get_service_file_content(command: str, environment_variables: list[str]) -> str:
    env_lines = "\n".join(f"Environment={var}" for var in environment_variables)
    return f"""
[Unit]
After=network-online.target
Wants=network-online.target

[Service]
User={os.environ.get("SUDO_USER") or getpass.getuser()}
WorkingDirectory={Path.cwd()}
{env_lines}
ExecStart={command}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
    """


def _get_service_file_path(name: str) -> Path:
    return Path(f"/etc/systemd/system/{name}.service")


def _enable_service(name: str) -> None:
    _run_systemctl_command("enable", name)


def _disable_service(name: str) -> None:
    _run_systemctl_command("disable", name)


def _start_service(name: str) -> None:
    _run_systemctl_command("start", name)


def _stop_service(name: str) -> None:
    _run_systemctl_command("stop", name)


def _run_systemctl_command(command: str, service_name: str) -> None:
    check_call([
        "systemctl", command, service_name
    ])


if __name__ == "__main__":
    cli()