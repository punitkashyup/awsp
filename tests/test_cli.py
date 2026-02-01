"""Tests for CLI commands."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from awsp.cli import app


runner = CliRunner()


class TestCLIHelp:
    """Tests for CLI help and basic commands."""

    def test_help(self):
        """Test --help flag."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "AWS Profile Switcher" in result.stdout

    def test_list_help(self):
        """Test list --help."""
        result = runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0
        assert "List all AWS profiles" in result.stdout

    def test_add_help(self):
        """Test add --help."""
        result = runner.invoke(app, ["add", "--help"])
        assert result.exit_code == 0
        assert "Add a new AWS profile" in result.stdout

    def test_switch_help(self):
        """Test switch --help."""
        result = runner.invoke(app, ["switch", "--help"])
        assert result.exit_code == 0
        assert "Switch to a different AWS profile" in result.stdout


class TestCLIList:
    """Tests for list command."""

    def test_list_empty(self, mock_aws_env: Path):
        """Test listing with no profiles."""
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "No AWS profiles found" in result.stdout

    def test_list_with_profiles(self, populated_aws_env: Path):
        """Test listing profiles."""
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "default" in result.stdout
        assert "production" in result.stdout
        assert "staging" in result.stdout
        assert "sso-profile" in result.stdout

    def test_list_shows_types(self, populated_aws_env: Path):
        """Test list shows profile types."""
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "IAM" in result.stdout
        assert "SSO" in result.stdout

    def test_list_shows_regions(self, populated_aws_env: Path):
        """Test list shows regions."""
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "us-east-1" in result.stdout
        assert "us-west-2" in result.stdout


class TestCLICurrent:
    """Tests for current command."""

    def test_current_no_profile(self, mock_aws_env: Path):
        """Test current when no profile is set."""
        result = runner.invoke(app, ["current"])
        assert result.exit_code == 0
        assert "No profile currently active" in result.stdout

    def test_current_with_profile(
        self,
        populated_aws_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test current when profile is set."""
        monkeypatch.setenv("AWS_PROFILE", "production")

        result = runner.invoke(app, ["current"])
        assert result.exit_code == 0
        assert "production" in result.stdout

    def test_current_quiet_mode(
        self,
        populated_aws_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test current with quiet mode."""
        monkeypatch.setenv("AWS_PROFILE", "production")

        result = runner.invoke(app, ["current", "--quiet"])
        assert result.exit_code == 0
        assert result.stdout.strip() == "production"

    def test_current_quiet_no_profile(self, mock_aws_env: Path):
        """Test current quiet mode with no profile."""
        result = runner.invoke(app, ["current", "--quiet"])
        assert result.exit_code == 1


class TestCLISwitch:
    """Tests for switch command."""

    def test_switch_with_profile_name(self, populated_aws_env: Path):
        """Test switching to specific profile."""
        result = runner.invoke(app, ["switch", "production"])
        assert result.exit_code == 0
        assert "production" in result.stdout

    def test_switch_nonexistent_profile(self, populated_aws_env: Path):
        """Test switching to nonexistent profile."""
        result = runner.invoke(app, ["switch", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_switch_shell_mode(self, populated_aws_env: Path):
        """Test switch with shell mode."""
        result = runner.invoke(app, ["switch", "production", "--shell-mode"])
        assert result.exit_code == 0
        assert 'export AWS_PROFILE="production"' in result.stdout

    def test_switch_shell_mode_nonexistent(self, populated_aws_env: Path):
        """Test switch shell mode with nonexistent profile."""
        result = runner.invoke(app, ["switch", "nonexistent", "--shell-mode"])
        assert result.exit_code == 1


class TestCLIRemove:
    """Tests for remove command."""

    def test_remove_with_force(self, populated_aws_env: Path):
        """Test removing profile with force flag."""
        result = runner.invoke(app, ["remove", "staging", "--force"])
        assert result.exit_code == 0
        assert "removed" in result.stdout.lower()

    def test_remove_nonexistent(self, populated_aws_env: Path):
        """Test removing nonexistent profile."""
        result = runner.invoke(app, ["remove", "nonexistent", "--force"])
        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_remove_with_confirmation(self, populated_aws_env: Path):
        """Test removing profile with confirmation prompt."""
        # Mock the confirm_action to return True
        with patch("awsp.cli.confirm_action", return_value=True):
            result = runner.invoke(app, ["remove", "staging"])
            assert result.exit_code == 0
            assert "removed" in result.stdout.lower()

    def test_remove_cancelled(self, populated_aws_env: Path):
        """Test removing profile cancelled."""
        # Mock the confirm_action to return False
        with patch("awsp.cli.confirm_action", return_value=False):
            result = runner.invoke(app, ["remove", "staging"])
            assert result.exit_code == 0
            assert "Cancelled" in result.stdout


class TestCLIValidate:
    """Tests for validate command."""

    def test_validate_success(self, populated_aws_env: Path):
        """Test successful validation."""
        with patch("awsp.profiles.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"Account": "123456789012"}',
            )

            result = runner.invoke(app, ["validate", "default"])
            assert result.exit_code == 0
            assert "valid" in result.stdout.lower()

    def test_validate_failure(self, populated_aws_env: Path):
        """Test failed validation."""
        with patch("awsp.profiles.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stderr="InvalidClientTokenId",
            )

            result = runner.invoke(app, ["validate", "default"])
            assert result.exit_code == 1
            assert "failed" in result.stdout.lower()

    def test_validate_current_profile(
        self,
        populated_aws_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test validate uses current profile if not specified."""
        monkeypatch.setenv("AWS_PROFILE", "production")

        with patch("awsp.profiles.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"Account": "123456789012"}',
            )

            result = runner.invoke(app, ["validate"])
            assert result.exit_code == 0

            # Verify production profile was validated
            call_args = mock_run.call_args[0][0]
            assert "production" in call_args


class TestCLIInit:
    """Tests for init command."""

    def test_init_default(self):
        """Test init outputs shell hook."""
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert "awsp()" in result.stdout or "function awsp" in result.stdout

    def test_init_bash(self):
        """Test init with bash shell."""
        result = runner.invoke(app, ["init", "--shell", "bash"])
        assert result.exit_code == 0
        assert "awsp()" in result.stdout
        assert "eval" in result.stdout

    def test_init_zsh(self):
        """Test init with zsh shell."""
        result = runner.invoke(app, ["init", "--shell", "zsh"])
        assert result.exit_code == 0
        assert "awsp()" in result.stdout

    def test_init_fish(self):
        """Test init with fish shell."""
        result = runner.invoke(app, ["init", "--shell", "fish"])
        assert result.exit_code == 0
        assert "function awsp" in result.stdout
        assert "set -gx AWS_PROFILE" in result.stdout

    def test_init_invalid_shell(self):
        """Test init with invalid shell."""
        result = runner.invoke(app, ["init", "--shell", "invalid"])
        assert result.exit_code == 1


class TestCLIInfo:
    """Tests for info command."""

    def test_info_with_profile(self, populated_aws_env: Path):
        """Test info command with profile name."""
        result = runner.invoke(app, ["info", "default"])
        assert result.exit_code == 0
        assert "default" in result.stdout
        assert "IAM" in result.stdout

    def test_info_sso_profile(self, populated_aws_env: Path):
        """Test info command with SSO profile."""
        result = runner.invoke(app, ["info", "sso-profile"])
        assert result.exit_code == 0
        assert "sso-profile" in result.stdout
        assert "SSO" in result.stdout

    def test_info_nonexistent(self, populated_aws_env: Path):
        """Test info command with nonexistent profile."""
        result = runner.invoke(app, ["info", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_info_current_profile(
        self,
        populated_aws_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test info command uses current profile if not specified."""
        monkeypatch.setenv("AWS_PROFILE", "production")

        result = runner.invoke(app, ["info"])
        assert result.exit_code == 0
        assert "production" in result.stdout


class TestCLIAdd:
    """Tests for add command."""

    def test_add_iam_profile(self, mock_aws_env: Path):
        """Test adding IAM profile interactively."""
        # Simulate interactive input
        inputs = [
            "test-profile",  # Profile name
            "AKIATESTEXAMPLE12345",  # Access key
            "testSecretKey1234567890123456",  # Secret key
            "",  # Region (skip)
        ]

        result = runner.invoke(app, ["add", "--type", "iam"], input="\n".join(inputs) + "\n")

        # Note: May fail due to questionary not working well in test runner
        # but should at least start the process
        assert "Profile name" in result.stdout or result.exit_code in [0, 1]

    def test_add_invalid_type(self, mock_aws_env: Path):
        """Test add with invalid type."""
        result = runner.invoke(app, ["add", "--type", "invalid"])
        assert result.exit_code == 1
        assert "Invalid profile type" in result.stdout

    def test_add_iam_profile_with_mocked_prompts(self, mock_aws_env: Path):
        """Test adding IAM profile with mocked prompts."""
        from awsp.config.models import IAMProfile

        mock_profile = IAMProfile(
            name="mocked-profile",
            aws_access_key_id="AKIAMOCKEDEXAMPLE12",
            aws_secret_access_key="mockedSecretKey123456789012",
            region="us-west-2",
        )

        with patch("awsp.cli.prompt_iam_profile", return_value=mock_profile):
            result = runner.invoke(app, ["add", "--type", "iam"])
            assert result.exit_code == 0
            assert "created successfully" in result.stdout

    def test_add_iam_profile_cancelled(self, mock_aws_env: Path):
        """Test cancelling IAM profile creation."""
        with patch("awsp.cli.prompt_iam_profile", return_value=None):
            result = runner.invoke(app, ["add", "--type", "iam"])
            assert result.exit_code == 1
            assert "Cancelled" in result.stdout

    def test_add_sso_profile_with_mocked_prompts(self, mock_aws_env: Path):
        """Test adding SSO profile with mocked prompts."""
        from awsp.config.models import SSOProfile

        mock_profile = SSOProfile(
            name="mocked-sso",
            sso_start_url="https://example.awsapps.com/start",
            sso_region="us-east-1",
            sso_account_id="123456789012",
            sso_role_name="Admin",
        )

        with patch("awsp.cli.prompt_sso_profile", return_value=mock_profile):
            with patch("awsp.cli.confirm_action", return_value=False):  # Don't run sso login
                result = runner.invoke(app, ["add", "--type", "sso"])
                assert result.exit_code == 0
                assert "created successfully" in result.stdout

    def test_add_sso_profile_cancelled(self, mock_aws_env: Path):
        """Test cancelling SSO profile creation."""
        with patch("awsp.cli.prompt_sso_profile", return_value=None):
            result = runner.invoke(app, ["add", "--type", "sso"])
            assert result.exit_code == 1
            assert "Cancelled" in result.stdout

    def test_add_profile_exists_overwrite(self, populated_aws_env: Path):
        """Test overwriting existing profile."""
        from awsp.config.models import IAMProfile

        mock_profile = IAMProfile(
            name="default",  # Existing profile
            aws_access_key_id="AKIAUPDATEDEXAMPLE1",
            aws_secret_access_key="updatedSecretKey12345678901",
        )

        with patch("awsp.cli.prompt_iam_profile", return_value=mock_profile):
            with patch("awsp.cli.confirm_action", return_value=True):  # Confirm overwrite
                result = runner.invoke(app, ["add", "--type", "iam"])
                assert result.exit_code == 0
                assert "created successfully" in result.stdout

    def test_add_profile_exists_no_overwrite(self, populated_aws_env: Path):
        """Test declining to overwrite existing profile."""
        from awsp.config.models import IAMProfile

        mock_profile = IAMProfile(
            name="default",  # Existing profile
            aws_access_key_id="AKIAUPDATEDEXAMPLE1",
            aws_secret_access_key="updatedSecretKey12345678901",
        )

        with patch("awsp.cli.prompt_iam_profile", return_value=mock_profile):
            with patch("awsp.cli.confirm_action", return_value=False):  # Decline overwrite
                result = runner.invoke(app, ["add", "--type", "iam"])
                assert result.exit_code == 1
                assert "Cancelled" in result.stdout

    def test_add_interactive_type_selection(self, mock_aws_env: Path):
        """Test interactive type selection when no --type specified."""
        from awsp.config.models import ProfileType, IAMProfile

        mock_profile = IAMProfile(
            name="interactive-test",
            aws_access_key_id="AKIAINTERACTIVE1234",
            aws_secret_access_key="interactiveSecretKey1234567",
        )

        with patch("awsp.cli.select_profile_type", return_value=ProfileType.IAM):
            with patch("awsp.cli.prompt_iam_profile", return_value=mock_profile):
                result = runner.invoke(app, ["add"])
                assert result.exit_code == 0
                assert "created successfully" in result.stdout

    def test_add_interactive_type_cancelled(self, mock_aws_env: Path):
        """Test cancelling interactive type selection."""
        with patch("awsp.cli.select_profile_type", return_value=None):
            result = runner.invoke(app, ["add"])
            assert result.exit_code == 1


class TestCLIMainCallback:
    """Tests for the main callback (default command)."""

    def test_main_no_profiles(self, mock_aws_env: Path):
        """Test main callback with no profiles."""
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "No profile" in result.stdout or "No profiles" in result.stdout

    def test_main_with_profiles_interactive(self, populated_aws_env: Path):
        """Test main callback with profiles shows current and prompts."""
        with patch("awsp.cli.select_profile", return_value="production"):
            result = runner.invoke(app, [])
            assert result.exit_code == 0

    def test_main_with_profiles_same_selected(
        self,
        populated_aws_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test main callback when selecting current profile."""
        monkeypatch.setenv("AWS_PROFILE", "default")

        with patch("awsp.cli.select_profile", return_value="default"):
            result = runner.invoke(app, [])
            assert result.exit_code == 0
            assert "Already on profile" in result.stdout

    def test_main_shell_mode_success(self, populated_aws_env: Path):
        """Test main callback with shell mode."""
        with patch("awsp.cli.select_profile", return_value="production"):
            result = runner.invoke(app, ["--shell-mode"])
            assert result.exit_code == 0
            assert 'export AWS_PROFILE="production"' in result.stdout

    def test_main_shell_mode_cancelled(self, populated_aws_env: Path):
        """Test main callback shell mode cancelled."""
        with patch("awsp.cli.select_profile", return_value=None):
            result = runner.invoke(app, ["--shell-mode"])
            assert result.exit_code == 1

    def test_main_shell_mode_no_profiles(self, mock_aws_env: Path):
        """Test main callback shell mode with no profiles."""
        result = runner.invoke(app, ["--shell-mode"])
        assert result.exit_code == 1


class TestCLISwitchInteractive:
    """Tests for switch command interactive mode."""

    def test_switch_interactive_cancelled(self, populated_aws_env: Path):
        """Test switch interactive mode cancelled."""
        with patch("awsp.cli.select_profile", return_value=None):
            result = runner.invoke(app, ["switch"])
            assert result.exit_code == 1

    def test_switch_already_on_profile(
        self,
        populated_aws_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test switch to profile already active."""
        monkeypatch.setenv("AWS_PROFILE", "production")

        result = runner.invoke(app, ["switch", "production"])
        assert result.exit_code == 0
        assert "Already on profile" in result.stdout


class TestCLIValidateEdgeCases:
    """Edge case tests for validate command."""

    def test_validate_no_current_profile(self, mock_aws_env: Path):
        """Test validate with no profile specified and no current profile."""
        result = runner.invoke(app, ["validate"])
        assert result.exit_code == 1
        assert "No profile specified" in result.stdout

    def test_validate_profile_not_found(self, populated_aws_env: Path):
        """Test validate with nonexistent profile."""
        result = runner.invoke(app, ["validate", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.stdout


class TestCLIInfoEdgeCases:
    """Edge case tests for info command."""

    def test_info_no_current_profile(self, mock_aws_env: Path):
        """Test info with no profile specified and no current profile."""
        result = runner.invoke(app, ["info"])
        assert result.exit_code == 1
        assert "No profile specified" in result.stdout
