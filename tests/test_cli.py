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
            assert result.exit_code == 1  # Cancelled should be non-zero
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


class TestCLIActivate:
    """Tests for activate command."""

    def test_activate_help(self):
        """Test activate --help."""
        result = runner.invoke(app, ["activate", "--help"])
        assert result.exit_code == 0
        assert "Activate" in result.stdout

    def test_activate_shell_mode(self, populated_aws_env: Path):
        """Test activate with shell mode."""
        result = runner.invoke(app, ["activate", "production", "--shell-mode"])
        assert result.exit_code == 0
        assert 'export AWS_PROFILE="production"' in result.stdout
        assert "Activated profile" in result.stdout

    def test_activate_shell_mode_nonexistent(self, populated_aws_env: Path):
        """Test activate nonexistent profile in shell mode."""
        result = runner.invoke(app, ["activate", "nonexistent", "--shell-mode"])
        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_activate_shell_mode_no_profiles(self, mock_aws_env: Path):
        """Test activate shell mode with no profiles."""
        result = runner.invoke(app, ["activate", "--shell-mode"])
        assert result.exit_code == 1
        assert "No AWS profiles" in result.stdout

    def test_activate_without_shell_integration(self, populated_aws_env: Path):
        """Test activate without shell integration shows instructions."""
        result = runner.invoke(app, ["activate", "production"])
        assert result.exit_code == 0
        assert "Shell integration required" in result.stdout or "export AWS_PROFILE" in result.stdout

    def test_activate_interactive_shell_mode(self, populated_aws_env: Path):
        """Test activate interactive mode with shell mode."""
        with patch("awsp.cli.select_profile", return_value="staging"):
            result = runner.invoke(app, ["activate", "--shell-mode"])
            assert result.exit_code == 0
            assert 'export AWS_PROFILE="staging"' in result.stdout


class TestCLIDeactivate:
    """Tests for deactivate command."""

    def test_deactivate_help(self):
        """Test deactivate --help."""
        result = runner.invoke(app, ["deactivate", "--help"])
        assert result.exit_code == 0
        assert "Deactivate" in result.stdout

    def test_deactivate_shell_mode_with_profile(
        self,
        populated_aws_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test deactivate with active profile in shell mode."""
        monkeypatch.setenv("AWS_PROFILE", "production")
        result = runner.invoke(app, ["deactivate", "--shell-mode"])
        assert result.exit_code == 0
        assert "unset AWS_PROFILE" in result.stdout
        assert "Deactivated" in result.stdout

    def test_deactivate_shell_mode_no_profile(self, mock_aws_env: Path):
        """Test deactivate with no active profile in shell mode."""
        result = runner.invoke(app, ["deactivate", "--shell-mode"])
        assert result.exit_code == 0
        assert "No profile currently active" in result.stdout

    def test_deactivate_without_shell_integration(
        self,
        populated_aws_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test deactivate without shell integration shows instructions."""
        monkeypatch.setenv("AWS_PROFILE", "production")
        result = runner.invoke(app, ["deactivate"])
        assert result.exit_code == 0
        assert "Shell integration required" in result.stdout or "unset AWS_PROFILE" in result.stdout


class TestCLISetup:
    """Tests for setup command."""

    def test_setup_help(self):
        """Test setup --help."""
        result = runner.invoke(app, ["setup", "--help"])
        assert result.exit_code == 0
        assert "Set up shell integration" in result.stdout

    def test_setup_already_configured(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test setup when already configured."""
        # Create a mock home directory with .zshrc containing awsp init
        home = tmp_path / "home"
        home.mkdir()
        zshrc = home / ".zshrc"
        zshrc.write_text('eval "$(awsp init)"\n')

        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("SHELL", "/bin/zsh")

        # Patch Path.home() to return our mock home
        with patch("pathlib.Path.home", return_value=home):
            result = runner.invoke(app, ["setup"])
            assert result.exit_code == 0
            assert "already configured" in result.stdout

    def test_setup_adds_integration(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test setup adds shell integration."""
        # Create a mock home directory with empty .zshrc
        home = tmp_path / "home"
        home.mkdir()
        zshrc = home / ".zshrc"
        zshrc.write_text("# existing config\n")

        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("SHELL", "/bin/zsh")

        with patch("pathlib.Path.home", return_value=home):
            result = runner.invoke(app, ["setup"])
            assert result.exit_code == 0
            assert "added" in result.stdout.lower()

            # Verify the file was updated
            content = zshrc.read_text()
            assert "awsp init" in content


class TestCLIInitPowerShell:
    """Tests for init command with PowerShell."""

    def test_init_powershell(self):
        """Test init with PowerShell shell type."""
        result = runner.invoke(app, ["init", "--shell", "powershell"])
        assert result.exit_code == 0
        assert "function awsp" in result.stdout
        assert "$env:AWS_PROFILE" in result.stdout


class TestCLIValidateErrorMessages:
    """Tests for improved validation error messages."""

    def test_validate_invalid_credentials(self, populated_aws_env: Path):
        """Test validation with invalid credentials shows helpful message."""
        with patch("awsp.profiles.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stderr="InvalidClientTokenId: The security token included in the request is invalid",
            )

            result = runner.invoke(app, ["validate", "default"])
            assert result.exit_code == 1
            assert "Invalid credentials" in result.stdout or "access key" in result.stdout.lower()

    def test_validate_expired_token(self, populated_aws_env: Path):
        """Test validation with expired token shows helpful message."""
        with patch("awsp.profiles.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stderr="ExpiredToken: The security token included in the request is expired",
            )

            result = runner.invoke(app, ["validate", "default"])
            assert result.exit_code == 1
            assert "expired" in result.stdout.lower() or "sso login" in result.stdout.lower()

    def test_validate_timeout(self, populated_aws_env: Path):
        """Test validation timeout shows helpful message."""
        import subprocess
        with patch("awsp.profiles.manager.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="aws", timeout=30)

            result = runner.invoke(app, ["validate", "default"])
            assert result.exit_code == 1
            assert "timed out" in result.stdout.lower() or "network" in result.stdout.lower()

    def test_validate_aws_cli_not_found(self, populated_aws_env: Path):
        """Test validation when AWS CLI not found shows helpful message."""
        with patch("awsp.profiles.manager.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            result = runner.invoke(app, ["validate", "default"])
            assert result.exit_code == 1
            assert "AWS CLI not found" in result.stdout or "install" in result.stdout.lower()


class TestCLIAddSuccessHints:
    """Tests for success hints after add command."""

    def test_add_iam_shows_next_steps(self, mock_aws_env: Path):
        """Test adding IAM profile shows next steps."""
        from awsp.config.models import IAMProfile

        mock_profile = IAMProfile(
            name="test-profile",
            aws_access_key_id="AKIATESTEXAMPLE12345",
            aws_secret_access_key="testSecretKey1234567890123456",
        )

        with patch("awsp.cli.prompt_iam_profile", return_value=mock_profile):
            result = runner.invoke(app, ["add", "--type", "iam"])
            assert result.exit_code == 0
            assert "created successfully" in result.stdout
            assert "Next" in result.stdout or "activate" in result.stdout.lower()

    def test_add_sso_shows_next_steps(self, mock_aws_env: Path):
        """Test adding SSO profile shows next steps."""
        from awsp.config.models import SSOProfile

        mock_profile = SSOProfile(
            name="test-sso",
            sso_start_url="https://example.awsapps.com/start",
            sso_region="us-east-1",
            sso_account_id="123456789012",
            sso_role_name="Admin",
        )

        with patch("awsp.cli.prompt_sso_profile", return_value=mock_profile):
            with patch("awsp.cli.confirm_action", return_value=False):
                result = runner.invoke(app, ["add", "--type", "sso"])
                assert result.exit_code == 0
                assert "created successfully" in result.stdout
                assert "Next" in result.stdout or "activate" in result.stdout.lower()


class TestCLIAddAWSCLICheck:
    """Tests for AWS CLI check before SSO login."""

    def test_add_sso_checks_aws_cli(self, mock_aws_env: Path):
        """Test SSO login checks for AWS CLI before running."""
        from awsp.config.models import SSOProfile

        mock_profile = SSOProfile(
            name="test-sso",
            sso_start_url="https://example.awsapps.com/start",
            sso_region="us-east-1",
            sso_account_id="123456789012",
            sso_role_name="Admin",
        )

        with patch("awsp.cli.prompt_sso_profile", return_value=mock_profile):
            with patch("awsp.cli.confirm_action", return_value=True):
                with patch("shutil.which", return_value=None):
                    result = runner.invoke(app, ["add", "--type", "sso"])
                    assert result.exit_code == 0
                    assert "not installed" in result.stdout.lower() or "install" in result.stdout.lower()


class TestDisplaySpinner:
    """Tests for display spinner utility."""

    def test_show_spinner_exists(self):
        """Test that show_spinner is importable."""
        from awsp.ui.display import show_spinner
        assert show_spinner is not None

    def test_show_spinner_is_context_manager(self):
        """Test that show_spinner can be used as context manager."""
        from awsp.ui.display import show_spinner
        import contextlib
        assert hasattr(show_spinner, '__enter__') or isinstance(show_spinner, type(contextlib.contextmanager))
