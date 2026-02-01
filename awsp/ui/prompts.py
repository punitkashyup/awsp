"""Interactive prompts for user input."""

from typing import List, Optional

import questionary
from questionary import Style

from awsp.config.models import IAMProfile, SSOProfile, ProfileType


# Custom style for prompts
custom_style = Style([
    ("qmark", "fg:cyan bold"),
    ("question", "bold"),
    ("answer", "fg:green bold"),
    ("pointer", "fg:cyan bold"),
    ("highlighted", "fg:cyan bold"),
    ("selected", "fg:green"),
])


def select_profile(profiles: List[str], current: Optional[str] = None) -> Optional[str]:
    """Interactive profile selector with fuzzy search.

    Returns selected profile name or None if cancelled.
    """
    if not profiles:
        return None

    choices = []
    for name in sorted(profiles):
        label = f"{name} (current)" if name == current else name
        choices.append(questionary.Choice(title=label, value=name))

    result = questionary.select(
        "Select AWS profile:",
        choices=choices,
        style=custom_style,
        use_shortcuts=False,
        use_arrow_keys=True,
    ).ask()

    return result


def select_profile_type() -> Optional[ProfileType]:
    """Prompt user to select profile type."""
    choices = [
        questionary.Choice(title="IAM (Access Key / Secret Key)", value=ProfileType.IAM),
        questionary.Choice(title="SSO (AWS Single Sign-On)", value=ProfileType.SSO),
    ]

    result = questionary.select(
        "Select profile type:",
        choices=choices,
        style=custom_style,
    ).ask()

    return result


def prompt_iam_profile(existing_name: Optional[str] = None) -> Optional[IAMProfile]:
    """Prompt user for IAM profile details.

    Returns IAMProfile or None if cancelled.
    """
    # Profile name
    name = questionary.text(
        "Profile name:",
        default=existing_name or "",
        validate=lambda x: len(x.strip()) > 0 or "Profile name is required",
        style=custom_style,
    ).ask()

    if name is None:
        return None

    # Access key
    access_key = questionary.text(
        "AWS Access Key ID (starts with AKIA):",
        instruction="Find in: IAM → Users → Security credentials → Access keys",
        validate=lambda x: (len(x.strip()) >= 16 and x.strip().startswith(("AKIA", "ASIA")))
                          or "Invalid access key format (should start with AKIA or ASIA)",
        style=custom_style,
    ).ask()

    if access_key is None:
        return None

    # Secret key (password input)
    secret_key = questionary.password(
        "AWS Secret Access Key:",
        validate=lambda x: len(x.strip()) >= 20 or "Secret key seems too short",
        style=custom_style,
    ).ask()

    if secret_key is None:
        return None

    # Region (optional)
    region = questionary.text(
        "Default region (optional, press Enter to skip):",
        default="",
        style=custom_style,
    ).ask()

    if region is None:
        return None

    return IAMProfile(
        name=name.strip(),
        aws_access_key_id=access_key.strip(),
        aws_secret_access_key=secret_key.strip(),
        region=region.strip() or None,
    )


def prompt_sso_profile(existing_name: Optional[str] = None) -> Optional[SSOProfile]:
    """Prompt user for SSO profile details.

    Returns SSOProfile or None if cancelled.
    """
    # Profile name
    name = questionary.text(
        "Profile name:",
        default=existing_name or "",
        validate=lambda x: len(x.strip()) > 0 or "Profile name is required",
        style=custom_style,
    ).ask()

    if name is None:
        return None

    # SSO Start URL
    sso_start_url = questionary.text(
        "SSO Start URL (e.g., https://my-company.awsapps.com/start):",
        validate=lambda x: x.strip().startswith("https://") or "URL must start with https://",
        style=custom_style,
    ).ask()

    if sso_start_url is None:
        return None

    # SSO Region
    sso_region = questionary.text(
        "SSO Region:",
        default="us-east-1",
        validate=lambda x: len(x.strip()) > 0 or "SSO region is required",
        style=custom_style,
    ).ask()

    if sso_region is None:
        return None

    # Account ID
    sso_account_id = questionary.text(
        "AWS Account ID (12 digits):",
        instruction="Find in: AWS Console top-right → Account ID",
        validate=lambda x: (x.strip().isdigit() and len(x.strip()) == 12)
                          or "Account ID must be 12 digits",
        style=custom_style,
    ).ask()

    if sso_account_id is None:
        return None

    # Role name
    sso_role_name = questionary.text(
        "SSO Role Name (e.g., AdministratorAccess):",
        instruction="Find in: AWS SSO portal → AWS Account → Role name",
        validate=lambda x: len(x.strip()) > 0 or "Role name is required",
        style=custom_style,
    ).ask()

    if sso_role_name is None:
        return None

    # Default region (optional)
    region = questionary.text(
        "Default region for AWS operations (optional, press Enter to skip):",
        default="",
        style=custom_style,
    ).ask()

    if region is None:
        return None

    return SSOProfile(
        name=name.strip(),
        sso_start_url=sso_start_url.strip(),
        sso_region=sso_region.strip(),
        sso_account_id=sso_account_id.strip(),
        sso_role_name=sso_role_name.strip(),
        region=region.strip() or None,
    )


def confirm_action(message: str, default: bool = False) -> bool:
    """Prompt user to confirm an action."""
    result = questionary.confirm(
        message,
        default=default,
        style=custom_style,
    ).ask()

    return result if result is not None else False
