"""Tests for profile manager."""

import configparser
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from awsp.profiles.manager import ProfileManager
from awsp.config.models import IAMProfile, SSOProfile


class TestProfileManagerList:
    """Tests for ProfileManager list operations."""

    def test_list_empty_profiles(self, mock_aws_env: Path):
        """Test listing with no profiles."""
        manager = ProfileManager()
        profiles = manager.list_profiles()
        assert profiles == {}

    def test_list_profiles(self, populated_aws_env: Path):
        """Test listing all profiles."""
        manager = ProfileManager()
        profiles = manager.list_profiles()

        assert len(profiles) >= 4
        assert "default" in profiles
        assert "production" in profiles
        assert "staging" in profiles
        assert "sso-profile" in profiles

    def test_get_profile_names(self, populated_aws_env: Path):
        """Test getting profile names."""
        manager = ProfileManager()
        names = manager.get_profile_names()

        assert isinstance(names, list)
        assert "default" in names
        assert "production" in names
        assert names == sorted(names)  # Should be sorted

    def test_profile_exists(self, populated_aws_env: Path):
        """Test checking profile existence."""
        manager = ProfileManager()

        assert manager.profile_exists("default") is True
        assert manager.profile_exists("production") is True
        assert manager.profile_exists("nonexistent") is False

    def test_get_current_profile_none(self, mock_aws_env: Path):
        """Test getting current profile when none set."""
        manager = ProfileManager()
        assert manager.get_current_profile() is None

    def test_get_current_profile_set(
        self,
        populated_aws_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test getting current profile when set."""
        monkeypatch.setenv("AWS_PROFILE", "production")

        manager = ProfileManager()
        assert manager.get_current_profile() == "production"


class TestProfileManagerAddIAM:
    """Tests for ProfileManager IAM profile operations."""

    def test_add_iam_profile(self, mock_aws_env: Path):
        """Test adding a new IAM profile."""
        manager = ProfileManager()

        profile = IAMProfile(
            name="new-profile",
            aws_access_key_id="AKIANEWEXAMPLE12345",
            aws_secret_access_key="newSecretKey1234567890",
            region="us-west-2",
        )

        manager.add_iam_profile(profile)

        # Verify profile was added
        assert manager.profile_exists("new-profile")

        # Verify credentials file content
        creds = configparser.ConfigParser()
        creds.read(manager.credentials_path)

        assert creds.has_section("new-profile")
        assert creds.get("new-profile", "aws_access_key_id") == "AKIANEWEXAMPLE12345"
        assert creds.get("new-profile", "aws_secret_access_key") == "newSecretKey1234567890"

    def test_add_iam_profile_with_region(self, mock_aws_env: Path):
        """Test adding IAM profile creates config entry for region."""
        manager = ProfileManager()

        profile = IAMProfile(
            name="regional-profile",
            aws_access_key_id="AKIAREGEXAMPLE12345",
            aws_secret_access_key="regSecretKey1234567890",
            region="eu-west-1",
        )

        manager.add_iam_profile(profile)

        # Verify config file has region
        config = configparser.ConfigParser()
        config.read(manager.config_path)

        assert config.has_section("profile regional-profile")
        assert config.get("profile regional-profile", "region") == "eu-west-1"

    def test_add_iam_profile_overwrites_existing(self, populated_aws_env: Path):
        """Test adding IAM profile overwrites existing."""
        manager = ProfileManager()

        # Get original key
        original = manager.list_profiles()["default"]
        assert original.iam_profile.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"

        # Add with same name but different key
        profile = IAMProfile(
            name="default",
            aws_access_key_id="AKIAUPDATEDEXAMPLE12",
            aws_secret_access_key="updatedSecretKey123456",
        )

        manager.add_iam_profile(profile)

        # Verify it was updated
        creds = configparser.ConfigParser()
        creds.read(manager.credentials_path)

        assert creds.get("default", "aws_access_key_id") == "AKIAUPDATEDEXAMPLE12"

    def test_add_iam_profile_creates_backup(self, populated_aws_env: Path):
        """Test adding IAM profile creates backup."""
        manager = ProfileManager()

        profile = IAMProfile(
            name="backup-test",
            aws_access_key_id="AKIABACKUPEXAMPLE12",
            aws_secret_access_key="backupSecretKey123456",
        )

        manager.add_iam_profile(profile)

        # Check backup was created
        backup_path = manager.credentials_path.with_suffix(".bak")
        assert backup_path.exists()

    def test_add_iam_profile_correct_permissions(self, mock_aws_env: Path):
        """Test credentials file has correct permissions (600)."""
        manager = ProfileManager()

        profile = IAMProfile(
            name="perm-test",
            aws_access_key_id="AKIAPERMEXAMPLE1234",
            aws_secret_access_key="permSecretKey1234567890",
        )

        manager.add_iam_profile(profile)

        # Check permissions (600 = owner read/write only)
        import stat
        mode = manager.credentials_path.stat().st_mode
        assert stat.S_IMODE(mode) == 0o600


class TestProfileManagerAddSSO:
    """Tests for ProfileManager SSO profile operations."""

    def test_add_sso_profile(self, mock_aws_env: Path):
        """Test adding a new SSO profile."""
        manager = ProfileManager()

        profile = SSOProfile(
            name="new-sso",
            sso_start_url="https://example.awsapps.com/start",
            sso_region="us-east-1",
            sso_account_id="123456789012",
            sso_role_name="DeveloperAccess",
        )

        manager.add_sso_profile(profile)

        # Verify profile was added
        assert manager.profile_exists("new-sso")

        # Verify config file content
        config = configparser.ConfigParser()
        config.read(manager.config_path)

        assert config.has_section("profile new-sso")
        assert config.get("profile new-sso", "sso_start_url") == "https://example.awsapps.com/start"
        assert config.get("profile new-sso", "sso_account_id") == "123456789012"
        assert config.get("profile new-sso", "sso_role_name") == "DeveloperAccess"

    def test_add_sso_profile_with_session(self, mock_aws_env: Path):
        """Test adding SSO profile with session."""
        manager = ProfileManager()

        profile = SSOProfile(
            name="sso-session-test",
            sso_start_url="https://example.awsapps.com/start",
            sso_region="us-east-1",
            sso_account_id="123456789012",
            sso_role_name="Admin",
            sso_session="my-session",
            region="us-west-2",
        )

        manager.add_sso_profile(profile)

        config = configparser.ConfigParser()
        config.read(manager.config_path)

        assert config.get("profile sso-session-test", "sso_session") == "my-session"
        assert config.get("profile sso-session-test", "region") == "us-west-2"

    def test_add_sso_default_profile(self, mock_aws_env: Path):
        """Test adding SSO as default profile (no 'profile' prefix)."""
        manager = ProfileManager()

        profile = SSOProfile(
            name="default",
            sso_start_url="https://example.awsapps.com/start",
            sso_region="us-east-1",
            sso_account_id="123456789012",
            sso_role_name="Admin",
        )

        manager.add_sso_profile(profile)

        config = configparser.ConfigParser()
        config.read(manager.config_path)

        # Default profile should not have 'profile' prefix
        assert config.has_section("default")
        assert not config.has_section("profile default")


class TestProfileManagerRemove:
    """Tests for ProfileManager remove operations."""

    def test_remove_profile_from_credentials(self, populated_aws_env: Path):
        """Test removing profile from credentials file."""
        manager = ProfileManager()

        assert manager.profile_exists("production")

        result = manager.remove_profile("production")

        assert result is True
        assert manager.profile_exists("production") is False

        # Verify removed from credentials file
        creds = configparser.ConfigParser()
        creds.read(manager.credentials_path)
        assert not creds.has_section("production")

    def test_remove_profile_from_config(self, populated_aws_env: Path):
        """Test removing profile also removes from config."""
        manager = ProfileManager()

        result = manager.remove_profile("production")

        assert result is True

        # Verify removed from config file
        config = configparser.ConfigParser()
        config.read(manager.config_path)
        assert not config.has_section("profile production")

    def test_remove_sso_profile(self, populated_aws_env: Path):
        """Test removing SSO profile."""
        manager = ProfileManager()

        assert manager.profile_exists("sso-profile")

        result = manager.remove_profile("sso-profile")

        assert result is True
        assert manager.profile_exists("sso-profile") is False

    def test_remove_nonexistent_profile(self, populated_aws_env: Path):
        """Test removing nonexistent profile returns False."""
        manager = ProfileManager()

        result = manager.remove_profile("nonexistent-profile")

        assert result is False

    def test_remove_creates_backup(self, populated_aws_env: Path):
        """Test removing profile creates backup."""
        manager = ProfileManager()

        manager.remove_profile("production")

        backup_path = manager.credentials_path.with_suffix(".bak")
        assert backup_path.exists()


class TestProfileManagerValidate:
    """Tests for ProfileManager validate operations."""

    def test_validate_success(self, populated_aws_env: Path):
        """Test successful validation."""
        manager = ProfileManager()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"Account": "123456789012", "Arn": "arn:aws:iam::123456789012:user/test"}',
            )

            success, message = manager.validate_profile("default")

            assert success is True
            assert "123456789012" in message

            # Verify correct command was called
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert "aws" in call_args[0][0]
            assert "--profile" in call_args[0][0]
            assert "default" in call_args[0][0]

    def test_validate_failure(self, populated_aws_env: Path):
        """Test failed validation returns user-friendly error message."""
        manager = ProfileManager()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stderr="An error occurred (InvalidClientTokenId)",
            )

            success, message = manager.validate_profile("default")

            assert success is False
            # Now returns user-friendly error instead of raw AWS error
            assert "Invalid credentials" in message or "access key" in message.lower()

    def test_validate_timeout(self, populated_aws_env: Path):
        """Test validation timeout."""
        manager = ProfileManager()

        with patch("subprocess.run") as mock_run:
            import subprocess
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="aws", timeout=30)

            success, message = manager.validate_profile("default")

            assert success is False
            assert "timed out" in message.lower()

    def test_validate_aws_not_found(self, populated_aws_env: Path):
        """Test validation when AWS CLI not found."""
        manager = ProfileManager()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            success, message = manager.validate_profile("default")

            assert success is False
            assert "not found" in message.lower()
