"""Parse AWS credentials and config files."""

import configparser
import os
from pathlib import Path
from typing import Dict, Optional

from awsp.config.models import IAMProfile, SSOProfile, ProfileInfo, ProfileType


def get_aws_credentials_path() -> Path:
    """Get path to AWS credentials file."""
    return Path(os.environ.get("AWS_SHARED_CREDENTIALS_FILE", Path.home() / ".aws" / "credentials"))


def get_aws_config_path() -> Path:
    """Get path to AWS config file."""
    return Path(os.environ.get("AWS_CONFIG_FILE", Path.home() / ".aws" / "config"))


def get_current_profile() -> Optional[str]:
    """Get currently active AWS profile from environment."""
    return os.environ.get("AWS_PROFILE") or os.environ.get("AWS_DEFAULT_PROFILE")


def _parse_credentials_file(path: Path) -> Dict[str, IAMProfile]:
    """Parse ~/.aws/credentials file.

    Format: [profile-name] (no 'profile' prefix, except 'default' is just [default])
    """
    profiles = {}

    if not path.exists():
        return profiles

    config = configparser.ConfigParser()
    config.read(path)

    for section in config.sections():
        # In credentials file, section name IS the profile name
        profile_name = section

        access_key = config.get(section, "aws_access_key_id", fallback=None)
        secret_key = config.get(section, "aws_secret_access_key", fallback=None)

        if access_key and secret_key:
            profiles[profile_name] = IAMProfile(
                name=profile_name,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region=config.get(section, "region", fallback=None),
                output=config.get(section, "output", fallback=None),
            )

    # Handle default profile if it exists
    if config.has_section("default"):
        access_key = config.get("default", "aws_access_key_id", fallback=None)
        secret_key = config.get("default", "aws_secret_access_key", fallback=None)
        if access_key and secret_key:
            profiles["default"] = IAMProfile(
                name="default",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region=config.get("default", "region", fallback=None),
                output=config.get("default", "output", fallback=None),
            )

    return profiles


def _parse_config_file(path: Path) -> tuple[Dict[str, SSOProfile], Dict[str, dict]]:
    """Parse ~/.aws/config file.

    Format: [profile profile-name] (with 'profile' prefix, except 'default' is just [default])

    Returns:
        Tuple of (sso_profiles, config_settings)
        - sso_profiles: SSO profile configurations
        - config_settings: Additional config for all profiles (region, output, etc.)
    """
    sso_profiles = {}
    config_settings = {}

    if not path.exists():
        return sso_profiles, config_settings

    config = configparser.ConfigParser()
    config.read(path)

    for section in config.sections():
        # Extract profile name (remove 'profile ' prefix if present)
        if section.startswith("profile "):
            profile_name = section[8:]  # Remove 'profile ' prefix
        elif section == "default":
            profile_name = "default"
        else:
            # Skip non-profile sections like [sso-session xxx]
            continue

        # Store config settings (region, output) for any profile
        config_settings[profile_name] = {
            "region": config.get(section, "region", fallback=None),
            "output": config.get(section, "output", fallback=None),
        }

        # Check if it's an SSO profile
        sso_start_url = config.get(section, "sso_start_url", fallback=None)
        sso_account_id = config.get(section, "sso_account_id", fallback=None)

        if sso_start_url and sso_account_id:
            sso_profiles[profile_name] = SSOProfile(
                name=profile_name,
                sso_start_url=sso_start_url,
                sso_region=config.get(section, "sso_region", fallback="us-east-1"),
                sso_account_id=sso_account_id,
                sso_role_name=config.get(section, "sso_role_name", fallback=""),
                region=config.get(section, "region", fallback=None),
                output=config.get(section, "output", fallback=None),
                sso_session=config.get(section, "sso_session", fallback=None),
            )

    return sso_profiles, config_settings


def parse_profiles() -> Dict[str, ProfileInfo]:
    """Parse all AWS profiles from credentials and config files.

    Merges profiles from both files and determines their type (IAM or SSO).
    """
    credentials_path = get_aws_credentials_path()
    config_path = get_aws_config_path()
    current_profile = get_current_profile()

    # Parse both files
    iam_profiles = _parse_credentials_file(credentials_path)
    sso_profiles, config_settings = _parse_config_file(config_path)

    # Merge into ProfileInfo
    profiles: Dict[str, ProfileInfo] = {}

    # Add IAM profiles
    for name, iam_profile in iam_profiles.items():
        # Get additional settings from config file
        settings = config_settings.get(name, {})
        region = iam_profile.region or settings.get("region")

        profiles[name] = ProfileInfo(
            name=name,
            profile_type=ProfileType.IAM,
            region=region,
            is_current=(name == current_profile),
            has_credentials=True,
            has_config=(name in config_settings),
            iam_profile=iam_profile,
        )

    # Add SSO profiles
    for name, sso_profile in sso_profiles.items():
        if name in profiles:
            # Profile already exists as IAM, skip SSO (IAM takes precedence)
            continue

        profiles[name] = ProfileInfo(
            name=name,
            profile_type=ProfileType.SSO,
            region=sso_profile.region,
            is_current=(name == current_profile),
            has_credentials=False,
            has_config=True,
            sso_account_id=sso_profile.sso_account_id,
            sso_profile=sso_profile,
        )

    # Add config-only profiles (no credentials, not SSO)
    for name in config_settings:
        if name not in profiles:
            settings = config_settings[name]
            profiles[name] = ProfileInfo(
                name=name,
                profile_type=ProfileType.IAM,  # Assume IAM if no SSO config
                region=settings.get("region"),
                is_current=(name == current_profile),
                has_credentials=False,
                has_config=True,
            )

    return profiles
