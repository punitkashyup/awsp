"""Display utilities for rich output."""

from contextlib import contextmanager
from typing import Dict, Generator, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from awsp.config.models import ProfileInfo, ProfileType


console = Console()


@contextmanager
def show_spinner(message: str) -> Generator[None, None, None]:
    """Show a spinner while an operation is in progress.

    Usage:
        with show_spinner("Validating credentials..."):
            do_slow_operation()
    """
    with console.status(f"[cyan]{message}[/cyan]", spinner="dots"):
        yield


def display_profiles_table(profiles: Dict[str, ProfileInfo]) -> None:
    """Display profiles in a rich table."""
    if not profiles:
        console.print("[yellow]No AWS profiles found.[/yellow]")
        console.print("\nTo add a profile, run: [cyan]awsp add[/cyan]")
        return

    table = Table(title="AWS Profiles", show_header=True, header_style="bold cyan")

    table.add_column("Profile", style="bold")
    table.add_column("Type", justify="center")
    table.add_column("Region", justify="center")
    table.add_column("Status", justify="center")

    for name in sorted(profiles.keys()):
        info = profiles[name]

        # Profile name with current indicator
        name_text = name
        if info.is_current:
            name_text = f"[green]{name}[/green]"

        # Profile type
        type_text = info.profile_type.value.upper()
        if info.profile_type == ProfileType.SSO:
            type_text = f"[blue]{type_text}[/blue]"

        # Region
        region_text = info.region or "[dim]-[/dim]"

        # Status
        status_parts = []
        if info.is_current:
            status_parts.append("[green]active[/green]")
        if not info.has_credentials and info.profile_type == ProfileType.IAM:
            status_parts.append("[yellow]no creds[/yellow]")

        status_text = " ".join(status_parts) if status_parts else "[dim]-[/dim]"

        table.add_row(name_text, type_text, region_text, status_text)

    console.print(table)


def display_current_profile(profile_name: Optional[str]) -> None:
    """Display the current active profile."""
    if profile_name:
        text = Text()
        text.append("Current profile: ", style="bold")
        text.append(profile_name, style="green bold")
        console.print(text)
    else:
        console.print("[yellow]No profile currently active[/yellow]")
        console.print("[dim]Using default credentials chain[/dim]")


def display_profile_info(info: ProfileInfo) -> None:
    """Display detailed information about a profile."""
    content = []

    content.append(f"[bold]Name:[/bold] {info.name}")
    content.append(f"[bold]Type:[/bold] {info.profile_type.value.upper()}")

    if info.region:
        content.append(f"[bold]Region:[/bold] {info.region}")

    if info.profile_type == ProfileType.SSO and info.sso_account_id:
        content.append(f"[bold]Account ID:[/bold] {info.sso_account_id}")

    if info.profile_type == ProfileType.IAM and info.iam_profile:
        content.append(f"[bold]Access Key:[/bold] {info.iam_profile.mask_access_key()}")

    status = "Active" if info.is_current else "Inactive"
    status_style = "green" if info.is_current else "dim"
    content.append(f"[bold]Status:[/bold] [{status_style}]{status}[/{status_style}]")

    panel = Panel(
        "\n".join(content),
        title=f"Profile: {info.name}",
        border_style="cyan",
    )
    console.print(panel)


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[red]✗[/red] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]![/yellow] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[cyan]ℹ[/cyan] {message}")
