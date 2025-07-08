from pathlib import Path
from subprocess import check_call
import getpass
import os

import click

@click.command()
@click.option("--name", required=True)
@click.option("--command", required=True)
def install_service(name: str, command: str):
    _write_service_file(name, command)
    _enable_service(name)
    _start_service(name)
    

def _write_service_file(name: str, command: str) -> None:
    file_path = _get_service_file_path(name)
    content = _get_service_file_content(command)
    if file_path.exists():
        raise FileExistsError(f"{name} is already configured at {file_path}")
    file_path.write_text(content)


def _get_service_file_content(command: str) -> str:
    return f"""
    [Unit]
    After=network.target

    [Service]
    User={os.environ.get("SUDO_USER") or getpass.getuser()}
    WorkingDirectory={Path.cwd()}
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


def _start_service(name: str) -> None:
    _run_systemctl_command("start", name)


def _run_systemctl_command(command: str, service_name: str) -> None:
    check_call([
        "systemctl", command, service_name
    ])


if __name__ == "__main__":
    install_service()