"""Main CLI application using Typer."""

from typing import Optional

import typer
from rich.console import Console

from awsp.config.models import ProfileType
from awsp.profiles.manager import ProfileManager
from awsp.shell.hooks import ShellType, get_shell_hook, get_export_command, detect_shell
from awsp.ui.display import (
    display_profiles_table,
    display_current_profile,
    display_profile_info,
    print_success,
    print_error,
    print_warning,
    print_info,
)
from awsp.ui.prompts import (
    select_profile,
    select_profile_type,
    prompt_iam_profile,
    prompt_sso_profile,
    confirm_action,
)


app = typer.Typer(
    name="awsp",
    help="AWS Profile Switcher - Manage AWS CLI profiles easily",
    add_completion=False,
    no_args_is_help=False,
)

console = Console()
manager = ProfileManager()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    shell_mode: bool = typer.Option(
        False,
        "--shell-mode",
        hidden=True,
        help="Output shell commands for eval (used by shell hook)",
    ),
):
    """AWS Profile Switcher - Manage AWS CLI profiles easily.

    Run without arguments for interactive profile switching.
    """
    # If a subcommand is invoked, don't run default behavior
    if ctx.invoked_subcommand is not None:
        return

    # Default behavior: show current profile and interactive switch
    if shell_mode:
        # Shell mode: just do the switch and output export command
        profiles = manager.get_profile_names()
        if not profiles:
            print_error("No AWS profiles found.")
            raise typer.Exit(1)

        current = manager.get_current_profile()
        selected = select_profile(profiles, current)

        if selected:
            print(get_export_command(selected))
            print(f'echo "Switched to profile: {selected}"')
        else:
            raise typer.Exit(1)
    else:
        # Interactive mode: show current, then select
        current = manager.get_current_profile()
        display_current_profile(current)
        console.print()

        profiles = manager.get_profile_names()
        if not profiles:
            print_warning("No profiles found. Add one with: awsp add")
            raise typer.Exit(0)

        selected = select_profile(profiles, current)

        if selected:
            if selected == current:
                print_info(f"Already on profile: {selected}")
            else:
                print_info(f"To switch to '{selected}', run:")
                console.print(f"  [cyan]export AWS_PROFILE={selected}[/cyan]")
                console.print()
                console.print("[dim]Tip: Add shell integration for automatic switching:[/dim]")
                console.print('  [dim]eval "$(awsp init)"[/dim]')


@app.command()
def list():
    """List all AWS profiles."""
    profiles = manager.list_profiles()
    display_profiles_table(profiles)


@app.command()
def switch(
    profile: Optional[str] = typer.Argument(None, help="Profile name to switch to"),
    shell_mode: bool = typer.Option(
        False,
        "--shell-mode",
        hidden=True,
        help="Output shell commands for eval",
    ),
):
    """Switch to a different AWS profile."""
    profiles_dict = manager.list_profiles()
    profile_names = list(profiles_dict.keys())

    if not profile_names:
        if shell_mode:
            print('echo "No AWS profiles found."')
            raise typer.Exit(1)
        print_error("No AWS profiles found.")
        raise typer.Exit(1)

    current = manager.get_current_profile()

    # If no profile specified, show interactive picker
    if profile is None:
        selected = select_profile(profile_names, current)
        if selected is None:
            raise typer.Exit(1)
        profile = selected

    # Validate profile exists
    if profile not in profile_names:
        if shell_mode:
            print(f'echo "Profile \'{profile}\' not found."')
            raise typer.Exit(1)
        print_error(f"Profile '{profile}' not found.")
        print_info("Available profiles:")
        for name in sorted(profile_names):
            console.print(f"  - {name}")
        raise typer.Exit(1)

    if shell_mode:
        # Output export command for shell eval
        print(get_export_command(profile))
        print(f'echo "Switched to profile: {profile}"')
    else:
        # Just print instructions
        if profile == current:
            print_info(f"Already on profile: {profile}")
        else:
            print_info(f"To switch to '{profile}', run:")
            console.print(f"  [cyan]export AWS_PROFILE={profile}[/cyan]")
            console.print()
            console.print("[dim]Or add shell integration: eval \"$(awsp init)\"[/dim]")


@app.command()
def add(
    profile_type: Optional[str] = typer.Option(
        None,
        "--type", "-t",
        help="Profile type: 'iam' or 'sso'",
    ),
):
    """Add a new AWS profile."""
    # Determine profile type
    if profile_type:
        try:
            ptype = ProfileType(profile_type.lower())
        except ValueError:
            print_error(f"Invalid profile type: {profile_type}")
            print_info("Valid types: iam, sso")
            raise typer.Exit(1)
    else:
        ptype = select_profile_type()
        if ptype is None:
            raise typer.Exit(1)

    # Prompt for profile details
    if ptype == ProfileType.IAM:
        profile = prompt_iam_profile()
        if profile is None:
            print_warning("Cancelled.")
            raise typer.Exit(1)

        # Check if profile already exists
        if manager.profile_exists(profile.name):
            if not confirm_action(f"Profile '{profile.name}' already exists. Overwrite?"):
                print_warning("Cancelled.")
                raise typer.Exit(1)

        manager.add_iam_profile(profile)
        print_success(f"Profile '{profile.name}' created successfully.")

    else:  # SSO
        profile = prompt_sso_profile()
        if profile is None:
            print_warning("Cancelled.")
            raise typer.Exit(1)

        # Check if profile already exists
        if manager.profile_exists(profile.name):
            if not confirm_action(f"Profile '{profile.name}' already exists. Overwrite?"):
                print_warning("Cancelled.")
                raise typer.Exit(1)

        manager.add_sso_profile(profile)
        print_success(f"Profile '{profile.name}' created successfully.")

        # Offer to run SSO login
        if confirm_action("Run 'aws sso login' now?"):
            import subprocess
            console.print()
            subprocess.run(["aws", "sso", "login", "--profile", profile.name])


@app.command()
def remove(
    profile: str = typer.Argument(..., help="Profile name to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Remove an AWS profile."""
    if not manager.profile_exists(profile):
        print_error(f"Profile '{profile}' not found.")
        raise typer.Exit(1)

    if not force:
        if not confirm_action(f"Remove profile '{profile}'?"):
            print_warning("Cancelled.")
            raise typer.Exit(0)

    if manager.remove_profile(profile):
        print_success(f"Profile '{profile}' removed.")
    else:
        print_error(f"Failed to remove profile '{profile}'.")
        raise typer.Exit(1)


@app.command()
def current(
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Only output profile name"),
):
    """Show the current active AWS profile."""
    profile = manager.get_current_profile()

    if quiet:
        if profile:
            print(profile)
        raise typer.Exit(0 if profile else 1)

    display_current_profile(profile)

    # Show additional info if profile exists
    if profile:
        profiles = manager.list_profiles()
        if profile in profiles:
            console.print()
            display_profile_info(profiles[profile])


@app.command()
def validate(
    profile: Optional[str] = typer.Argument(None, help="Profile to validate (default: current)"),
):
    """Validate AWS profile credentials using STS."""
    # Use current profile if not specified
    if profile is None:
        profile = manager.get_current_profile()
        if profile is None:
            print_error("No profile specified and no current profile set.")
            print_info("Usage: awsp validate <profile>")
            raise typer.Exit(1)

    if not manager.profile_exists(profile):
        print_error(f"Profile '{profile}' not found.")
        raise typer.Exit(1)

    print_info(f"Validating profile '{profile}'...")

    success, message = manager.validate_profile(profile)

    if success:
        print_success("Credentials are valid!")
        console.print()
        console.print(message)
    else:
        print_error("Validation failed.")
        console.print(message)
        raise typer.Exit(1)


@app.command()
def init(
    shell: Optional[str] = typer.Option(
        None,
        "--shell", "-s",
        help="Shell type: bash, zsh, or fish",
    ),
):
    """Output shell hook for profile switching integration.

    Add to your shell config:

    \b
    Bash (~/.bashrc):
        eval "$(awsp init)"

    \b
    Zsh (~/.zshrc):
        eval "$(awsp init)"

    \b
    Fish (~/.config/fish/config.fish):
        awsp init --shell fish | source
    """
    # Detect or use specified shell
    if shell:
        try:
            shell_type = ShellType(shell.lower())
        except ValueError:
            print(f"# Unknown shell: {shell}", file=__import__("sys").stderr)
            print("# Supported shells: bash, zsh, fish", file=__import__("sys").stderr)
            raise typer.Exit(1)
    else:
        shell_type = detect_shell()
        if shell_type is None:
            shell_type = ShellType.BASH  # Default to bash

    # Output the hook code
    print(get_shell_hook(shell_type))


@app.command()
def info(
    profile: Optional[str] = typer.Argument(None, help="Profile to show info for"),
):
    """Show detailed information about a profile."""
    if profile is None:
        profile = manager.get_current_profile()
        if profile is None:
            print_error("No profile specified and no current profile set.")
            raise typer.Exit(1)

    profiles = manager.list_profiles()

    if profile not in profiles:
        print_error(f"Profile '{profile}' not found.")
        raise typer.Exit(1)

    display_profile_info(profiles[profile])


if __name__ == "__main__":
    app()
