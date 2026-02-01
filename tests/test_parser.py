"""Tests for config parser."""

from pathlib import Path

import pytest

from awsp.config.parser import (
    get_aws_credentials_path,
    get_aws_config_path,
    get_current_profile,
    parse_profiles,
)
from awsp.config.models import ProfileType


class TestGetPaths:
    """Tests for path resolution functions."""

    def test_get_credentials_path_default(self, monkeypatch: pytest.MonkeyPatch):
        """Test default credentials path."""
        monkeypatch.delenv("AWS_SHARED_CREDENTIALS_FILE", raising=False)
        path = get_aws_credentials_path()
        assert path == Path.home() / ".aws" / "credentials"

    def test_get_credentials_path_custom(self, monkeypatch: pytest.MonkeyPatch):
        """Test custom credentials path from env var."""
        monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", "/custom/path/credentials")
        path = get_aws_credentials_path()
        assert path == Path("/custom/path/credentials")

    def test_get_config_path_default(self, monkeypatch: pytest.MonkeyPatch):
        """Test default config path."""
        monkeypatch.delenv("AWS_CONFIG_FILE", raising=False)
        path = get_aws_config_path()
        assert path == Path.home() / ".aws" / "config"

    def test_get_config_path_custom(self, monkeypatch: pytest.MonkeyPatch):
        """Test custom config path from env var."""
        monkeypatch.setenv("AWS_CONFIG_FILE", "/custom/path/config")
        path = get_aws_config_path()
        assert path == Path("/custom/path/config")


class TestGetCurrentProfile:
    """Tests for get_current_profile function."""

    def test_no_profile_set(self, monkeypatch: pytest.MonkeyPatch):
        """Test when no profile is set."""
        monkeypatch.delenv("AWS_PROFILE", raising=False)
        monkeypatch.delenv("AWS_DEFAULT_PROFILE", raising=False)
        assert get_current_profile() is None

    def test_aws_profile_set(self, monkeypatch: pytest.MonkeyPatch):
        """Test AWS_PROFILE environment variable."""
        monkeypatch.setenv("AWS_PROFILE", "production")
        monkeypatch.delenv("AWS_DEFAULT_PROFILE", raising=False)
        assert get_current_profile() == "production"

    def test_aws_default_profile_set(self, monkeypatch: pytest.MonkeyPatch):
        """Test AWS_DEFAULT_PROFILE environment variable."""
        monkeypatch.delenv("AWS_PROFILE", raising=False)
        monkeypatch.setenv("AWS_DEFAULT_PROFILE", "staging")
        assert get_current_profile() == "staging"

    def test_aws_profile_takes_precedence(self, monkeypatch: pytest.MonkeyPatch):
        """Test AWS_PROFILE takes precedence over AWS_DEFAULT_PROFILE."""
        monkeypatch.setenv("AWS_PROFILE", "production")
        monkeypatch.setenv("AWS_DEFAULT_PROFILE", "staging")
        assert get_current_profile() == "production"


class TestParseProfiles:
    """Tests for parse_profiles function."""

    def test_parse_empty_env(self, mock_aws_env: Path):
        """Test parsing with empty AWS files."""
        profiles = parse_profiles()
        assert profiles == {}

    def test_parse_credentials_only(
        self,
        temp_aws_dir: Path,
        sample_credentials_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test parsing credentials file only."""
        config_path = temp_aws_dir / "config"
        config_path.touch()

        monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(sample_credentials_file))
        monkeypatch.setenv("AWS_CONFIG_FILE", str(config_path))
        monkeypatch.delenv("AWS_PROFILE", raising=False)

        profiles = parse_profiles()

        assert "default" in profiles
        assert "production" in profiles
        assert "staging" in profiles

        # Check profile types
        assert profiles["default"].profile_type == ProfileType.IAM
        assert profiles["production"].profile_type == ProfileType.IAM

        # Check credentials flag
        assert profiles["default"].has_credentials is True
        assert profiles["production"].has_credentials is True

    def test_parse_config_with_sso(
        self,
        temp_aws_dir: Path,
        sample_config_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test parsing config file with SSO profiles."""
        credentials_path = temp_aws_dir / "credentials"
        credentials_path.touch()

        monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(credentials_path))
        monkeypatch.setenv("AWS_CONFIG_FILE", str(sample_config_file))
        monkeypatch.delenv("AWS_PROFILE", raising=False)

        profiles = parse_profiles()

        # SSO profile should be detected
        assert "sso-profile" in profiles
        assert profiles["sso-profile"].profile_type == ProfileType.SSO
        assert profiles["sso-profile"].sso_profile is not None
        assert profiles["sso-profile"].sso_account_id == "123456789012"

    def test_parse_merged_profiles(self, populated_aws_env: Path):
        """Test parsing merged credentials and config files."""
        profiles = parse_profiles()

        # Check we have all expected profiles
        assert "default" in profiles
        assert "production" in profiles
        assert "staging" in profiles
        assert "sso-profile" in profiles

        # Check default profile has both credentials and config
        assert profiles["default"].has_credentials is True
        assert profiles["default"].has_config is True
        assert profiles["default"].region == "us-east-1"

        # Check production profile
        assert profiles["production"].has_credentials is True
        assert profiles["production"].has_config is True
        assert profiles["production"].region == "us-west-2"

        # Check SSO profile
        assert profiles["sso-profile"].profile_type == ProfileType.SSO
        assert profiles["sso-profile"].has_credentials is False
        assert profiles["sso-profile"].has_config is True

    def test_parse_with_current_profile(
        self,
        populated_aws_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test parsing marks current profile correctly."""
        monkeypatch.setenv("AWS_PROFILE", "production")

        profiles = parse_profiles()

        assert profiles["production"].is_current is True
        assert profiles["default"].is_current is False
        assert profiles["staging"].is_current is False

    def test_iam_profile_data_accessible(self, populated_aws_env: Path):
        """Test IAM profile data is accessible."""
        profiles = parse_profiles()

        default = profiles["default"]
        assert default.iam_profile is not None
        assert default.iam_profile.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"

    def test_sso_profile_data_accessible(self, populated_aws_env: Path):
        """Test SSO profile data is accessible."""
        profiles = parse_profiles()

        sso = profiles["sso-profile"]
        assert sso.sso_profile is not None
        assert sso.sso_profile.sso_start_url == "https://my-company.awsapps.com/start"
        assert sso.sso_profile.sso_role_name == "AdministratorAccess"
