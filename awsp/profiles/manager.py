"""Profile management operations."""

import configparser
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from awsp.config.models import IAMProfile, SSOProfile, ProfileInfo, ProfileType
from awsp.config.parser import (
    parse_profiles,
    get_aws_credentials_path,
    get_aws_config_path,
    get_current_profile,
)


class ProfileManager:
    """Manages AWS CLI profiles."""

    def __init__(self):
        self.credentials_path = get_aws_credentials_path()
        self.config_path = get_aws_config_path()

    def list_profiles(self) -> Dict[str, ProfileInfo]:
        """List all AWS profiles."""
        return parse_profiles()

    def get_profile_names(self) -> List[str]:
        """Get list of profile names."""
        return sorted(parse_profiles().keys())

    def get_current_profile(self) -> Optional[str]:
        """Get currently active profile."""
        return get_current_profile()

    def profile_exists(self, name: str) -> bool:
        """Check if a profile exists."""
        return name in parse_profiles()

    def add_iam_profile(self, profile: IAMProfile) -> None:
        """Add or update an IAM profile.

        Writes credentials to ~/.aws/credentials and optionally config to ~/.aws/config.
        """
        # Ensure .aws directory exists
        self.credentials_path.parent.mkdir(parents=True, exist_ok=True)

        # Create backup of credentials file if it exists
        if self.credentials_path.exists():
            backup_path = self.credentials_path.with_suffix(".bak")
            shutil.copy2(self.credentials_path, backup_path)

        # Read existing credentials
        creds_config = configparser.ConfigParser()
        if self.credentials_path.exists():
            creds_config.read(self.credentials_path)

        # Add or update profile section
        section = profile.name
        if not creds_config.has_section(section) and section != "DEFAULT":
            creds_config.add_section(section)

        creds_config.set(section, "aws_access_key_id", profile.aws_access_key_id)
        creds_config.set(section, "aws_secret_access_key", profile.aws_secret_access_key)

        # Write credentials file
        self._write_config_file(creds_config, self.credentials_path, mode=0o600)

        # If region or output is specified, write to config file too
        if profile.region or profile.output:
            self._update_config_file(profile.name, profile.region, profile.output)

    def add_sso_profile(self, profile: SSOProfile) -> None:
        """Add or update an SSO profile.

        Writes to ~/.aws/config file.
        """
        # Ensure .aws directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Create backup of config file if it exists
        if self.config_path.exists():
            backup_path = self.config_path.with_suffix(".bak")
            shutil.copy2(self.config_path, backup_path)

        # Read existing config
        config = configparser.ConfigParser()
        if self.config_path.exists():
            config.read(self.config_path)

        # Determine section name (default has no prefix, others have 'profile ' prefix)
        section = "default" if profile.name == "default" else f"profile {profile.name}"

        if not config.has_section(section):
            config.add_section(section)

        # Set SSO configuration
        config.set(section, "sso_start_url", profile.sso_start_url)
        config.set(section, "sso_region", profile.sso_region)
        config.set(section, "sso_account_id", profile.sso_account_id)
        config.set(section, "sso_role_name", profile.sso_role_name)

        if profile.sso_session:
            config.set(section, "sso_session", profile.sso_session)

        if profile.region:
            config.set(section, "region", profile.region)

        if profile.output:
            config.set(section, "output", profile.output)

        # Write config file
        self._write_config_file(config, self.config_path, mode=0o644)

    def remove_profile(self, name: str) -> bool:
        """Remove a profile from both credentials and config files.

        Returns True if profile was found and removed.
        """
        removed = False

        # Remove from credentials file
        if self.credentials_path.exists():
            creds_config = configparser.ConfigParser()
            creds_config.read(self.credentials_path)

            if creds_config.has_section(name):
                # Create backup
                backup_path = self.credentials_path.with_suffix(".bak")
                shutil.copy2(self.credentials_path, backup_path)

                creds_config.remove_section(name)
                self._write_config_file(creds_config, self.credentials_path, mode=0o600)
                removed = True

        # Remove from config file
        if self.config_path.exists():
            config = configparser.ConfigParser()
            config.read(self.config_path)

            # Check both with and without 'profile ' prefix
            section = "default" if name == "default" else f"profile {name}"

            if config.has_section(section):
                # Create backup
                backup_path = self.config_path.with_suffix(".bak")
                shutil.copy2(self.config_path, backup_path)

                config.remove_section(section)
                self._write_config_file(config, self.config_path, mode=0o644)
                removed = True

        return removed

    def validate_profile(self, name: str) -> tuple[bool, str]:
        """Validate profile credentials using AWS STS.

        Returns (success, message) tuple.
        """
        try:
            result = subprocess.run(
                ["aws", "sts", "get-caller-identity", "--profile", name],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                error = result.stderr.strip()
                return False, self._format_validation_error(error, name)

        except subprocess.TimeoutExpired:
            return False, "Request timed out. Check your network connection or AWS service status."
        except FileNotFoundError:
            return False, "AWS CLI not found. Install with: brew install awscli (macOS) or pip install awscli"
        except Exception as e:
            return False, str(e)

    def _format_validation_error(self, error: str, profile_name: str) -> str:
        """Format AWS error messages with actionable suggestions."""
        if "InvalidClientTokenId" in error:
            return "Invalid credentials. Verify your access key ID is correct."
        elif "SignatureDoesNotMatch" in error:
            return "Invalid credentials. Verify your secret access key is correct."
        elif "ExpiredToken" in error:
            return f"Credentials expired. For SSO profiles, run: aws sso login --profile {profile_name}"
        elif "AccessDenied" in error:
            return "Access denied. Check that your credentials have the required permissions."
        elif "UnauthorizedAccess" in error:
            return f"Session expired. For SSO profiles, run: aws sso login --profile {profile_name}"
        elif "NoCredentialProviders" in error:
            return "No credentials found. Ensure the profile has valid credentials configured."
        else:
            return error

    def _update_config_file(self, profile_name: str, region: Optional[str], output: Optional[str]) -> None:
        """Update config file with region/output settings."""
        if not region and not output:
            return

        # Ensure .aws directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Read existing config
        config = configparser.ConfigParser()
        if self.config_path.exists():
            config.read(self.config_path)

        # Determine section name
        section = "default" if profile_name == "default" else f"profile {profile_name}"

        if not config.has_section(section):
            config.add_section(section)

        if region:
            config.set(section, "region", region)
        if output:
            config.set(section, "output", output)

        # Write config file
        self._write_config_file(config, self.config_path, mode=0o644)

    def _write_config_file(self, config: configparser.ConfigParser, path: Path, mode: int) -> None:
        """Write config to file atomically with proper permissions."""
        # Write to temp file first
        temp_path = path.with_suffix(".tmp")

        with open(temp_path, "w") as f:
            config.write(f)

        # Set proper permissions
        os.chmod(temp_path, mode)

        # Atomic rename
        temp_path.rename(path)
