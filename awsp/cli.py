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


def get_manager() -> ProfileManager:
    """Get a ProfileManager instance (created fresh for each command)."""
    return ProfileManager()


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
        profiles = get_manager().get_profile_names()
        if not profiles:
            print_error("No AWS profiles found.")
            raise typer.Exit(1)

        current = get_manager().get_current_profile()
        selected = select_profile(profiles, current)

        if selected:
            print(get_export_command(selected))
            print(f'echo "Switched to profile: {selected}"')
        else:
            raise typer.Exit(1)
    else:
        # Interactive mode: show current, then select
        current = get_manager().get_current_profile()
        display_current_profile(current)
        console.print()

        profiles = get_manager().get_profile_names()
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


@app.command(name="list")
def list_cmd():
    """List all AWS profiles."""
    profiles = get_manager().list_profiles()
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
    profiles_dict = get_manager().list_profiles()
    profile_names = list(profiles_dict.keys())

    if not profile_names:
        if shell_mode:
            print('echo "No AWS profiles found."')
            raise typer.Exit(1)
        print_error("No AWS profiles found.")
        raise typer.Exit(1)

    current = get_manager().get_current_profile()

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
        if get_manager().profile_exists(profile.name):
            if not confirm_action(f"Profile '{profile.name}' already exists. Overwrite?"):
                print_warning("Cancelled.")
                raise typer.Exit(1)

        get_manager().add_iam_profile(profile)
        print_success(f"Profile '{profile.name}' created successfully.")

    else:  # SSO
        profile = prompt_sso_profile()
        if profile is None:
            print_warning("Cancelled.")
            raise typer.Exit(1)

        # Check if profile already exists
        if get_manager().profile_exists(profile.name):
            if not confirm_action(f"Profile '{profile.name}' already exists. Overwrite?"):
                print_warning("Cancelled.")
                raise typer.Exit(1)

        get_manager().add_sso_profile(profile)
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
    if not get_manager().profile_exists(profile):
        print_error(f"Profile '{profile}' not found.")
        raise typer.Exit(1)

    if not force:
        if not confirm_action(f"Remove profile '{profile}'?"):
            print_warning("Cancelled.")
            raise typer.Exit(0)

    if get_manager().remove_profile(profile):
        print_success(f"Profile '{profile}' removed.")
    else:
        print_error(f"Failed to remove profile '{profile}'.")
        raise typer.Exit(1)


@app.command()
def current(
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Only output profile name"),
):
    """Show the current active AWS profile."""
    profile = get_manager().get_current_profile()

    if quiet:
        if profile:
            print(profile)
        raise typer.Exit(0 if profile else 1)

    display_current_profile(profile)

    # Show additional info if profile exists
    if profile:
        profiles = get_manager().list_profiles()
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
        profile = get_manager().get_current_profile()
        if profile is None:
            print_error("No profile specified and no current profile set.")
            print_info("Usage: awsp validate <profile>")
            raise typer.Exit(1)

    if not get_manager().profile_exists(profile):
        print_error(f"Profile '{profile}' not found.")
        raise typer.Exit(1)

    print_info(f"Validating profile '{profile}'...")

    success, message = get_manager().validate_profile(profile)

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
        profile = get_manager().get_current_profile()
        if profile is None:
            print_error("No profile specified and no current profile set.")
            raise typer.Exit(1)

    profiles = get_manager().list_profiles()

    if profile not in profiles:
        print_error(f"Profile '{profile}' not found.")
        raise typer.Exit(1)

    display_profile_info(profiles[profile])


@app.command()
def activate(
    profile: Optional[str] = typer.Argument(None, help="Profile name to activate"),
    shell_mode: bool = typer.Option(
        False,
        "--shell-mode",
        hidden=True,
        help="Output shell commands for eval",
    ),
):
    """Activate an AWS profile (sets AWS_PROFILE in current shell).

    Example:
        awsp activate my-profile

    Requires shell integration. Add to your ~/.zshrc:
        eval "$(awsp init)"
    """
    profiles_dict = get_manager().list_profiles()
    profile_names = list(profiles_dict.keys())

    if not profile_names:
        if shell_mode:
            print('echo "No AWS profiles found."')
            raise typer.Exit(1)
        print_error("No AWS profiles found.")
        raise typer.Exit(1)

    current = get_manager().get_current_profile()

    # If no profile specified, show interactive picker
    if profile is None:
        selected = select_profile(profile_names, current)
        if selected is None:
            if shell_mode:
                raise typer.Exit(1)
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
        print(f'echo "✓ Activated profile: {profile}"')
    else:
        # Without shell integration, just print instructions
        if profile == current:
            print_info(f"Already on profile: {profile}")
        else:
            print_warning("Shell integration required for 'activate' command.")
            print_info("Add this to your ~/.zshrc:")
            console.print('  [cyan]eval "$(awsp init)"[/cyan]')
            console.print()
            print_info(f"Or manually run:")
            console.print(f"  [cyan]export AWS_PROFILE={profile}[/cyan]")


@app.command()
def deactivate(
    shell_mode: bool = typer.Option(
        False,
        "--shell-mode",
        hidden=True,
        help="Output shell commands for eval",
    ),
):
    """Deactivate current AWS profile (unsets AWS_PROFILE).

    Example:
        awsp deactivate
    """
    from awsp.shell.hooks import get_unset_command

    current = get_manager().get_current_profile()

    if shell_mode:
        if current:
            print(get_unset_command())
            print(f'echo "✓ Deactivated profile: {current}"')
        else:
            print('echo "No profile currently active."')
    else:
        if current:
            print_warning("Shell integration required for 'deactivate' command.")
            print_info("Add this to your ~/.zshrc:")
            console.print('  [cyan]eval "$(awsp init)"[/cyan]')
            console.print()
            print_info(f"Or manually run:")
            console.print("  [cyan]unset AWS_PROFILE[/cyan]")
        else:
            print_info("No profile currently active.")


@app.command()
def setup():
    """Set up shell integration automatically.

    Detects your shell and adds the integration to your shell config file.

    Example:
        awsp setup
    """
    import os
    import sys
    from pathlib import Path

    shell_type = detect_shell()

    if shell_type is None:
        print_error("Could not detect your shell type.")
        print_info("Manually add to your shell config:")
        console.print('  [cyan]eval "$(awsp init)"[/cyan]')
        raise typer.Exit(1)

    # Determine config file based on shell
    home = Path.home()
    if shell_type == ShellType.ZSH:
        config_file = home / ".zshrc"
        integration_line = 'eval "$(awsp init)"'
        reload_cmd = f"source {config_file}"
    elif shell_type == ShellType.BASH:
        config_file = home / ".bashrc"
        integration_line = 'eval "$(awsp init)"'
        reload_cmd = f"source {config_file}"
    elif shell_type == ShellType.FISH:
        config_file = home / ".config" / "fish" / "config.fish"
        integration_line = "awsp init --shell fish | source"
        reload_cmd = f"source {config_file}"
    elif shell_type == ShellType.POWERSHELL:
        # PowerShell profile location
        if sys.platform == "win32":
            documents = home / "Documents"
            config_file = documents / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1"
        else:
            # PowerShell Core on macOS/Linux
            config_file = home / ".config" / "powershell" / "Microsoft.PowerShell_profile.ps1"
        integration_line = "Invoke-Expression (awsp init --shell powershell)"
        reload_cmd = ". $PROFILE"
    else:
        print_error(f"Unsupported shell: {shell_type}")
        raise typer.Exit(1)

    # Check if already configured
    if config_file.exists():
        content = config_file.read_text()
        if "awsp init" in content:
            print_success("Shell integration is already configured!")
            print_info(f"Config file: {config_file}")
            console.print()
            print_info("If it's not working, try reloading your shell:")
            console.print(f"  [cyan]{reload_cmd}[/cyan]")
            return

    # Add integration
    config_file.parent.mkdir(parents=True, exist_ok=True)

    with open(config_file, "a") as f:
        f.write(f"\n# AWSP: AWS Profile Switcher\n")
        f.write(f"# Added by 'awsp setup' - enables activate/deactivate commands\n")
        f.write(f"{integration_line}\n")

    print_success(f"Shell integration added to {config_file}")
    console.print()
    print_info("To activate, run:")
    console.print(f"  [cyan]{reload_cmd}[/cyan]")
    console.print()
    print_info("Or restart your terminal.")


if __name__ == "__main__":
    app()
