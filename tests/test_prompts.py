"""Tests for interactive prompts using questionary mocking."""

from unittest.mock import MagicMock, patch

import pytest

from awsp.ui.prompts import (
    select_profile,
    select_profile_type,
    prompt_iam_profile,
    prompt_sso_profile,
    confirm_action,
)
from awsp.config.models import ProfileType


class TestSelectProfile:
    """Tests for select_profile function."""

    def test_select_profile_empty_list(self):
        """Test selecting from empty profile list returns None."""
        result = select_profile([])
        assert result is None

    def test_select_profile_success(self):
        """Test successful profile selection."""
        with patch("awsp.ui.prompts.questionary") as mock_q:
            # Mock the select().ask() chain
            mock_select = MagicMock()
            mock_select.ask.return_value = "production"
            mock_q.select.return_value = mock_select
            mock_q.Choice = MagicMock(side_effect=lambda title, value: {"title": title, "value": value})

            result = select_profile(["default", "production", "staging"])

            assert result == "production"
            mock_q.select.assert_called_once()

    def test_select_profile_cancelled(self):
        """Test cancelled profile selection returns None."""
        with patch("awsp.ui.prompts.questionary") as mock_q:
            mock_select = MagicMock()
            mock_select.ask.return_value = None  # User pressed Ctrl+C
            mock_q.select.return_value = mock_select
            mock_q.Choice = MagicMock(side_effect=lambda title, value: {"title": title, "value": value})

            result = select_profile(["default", "production"])

            assert result is None

    def test_select_profile_marks_current(self):
        """Test current profile is marked in choices."""
        with patch("awsp.ui.prompts.questionary") as mock_q:
            mock_select = MagicMock()
            mock_select.ask.return_value = "default"
            mock_q.select.return_value = mock_select

            choices_created = []
            def capture_choice(title, value):
                choices_created.append({"title": title, "value": value})
                return {"title": title, "value": value}

            mock_q.Choice = MagicMock(side_effect=capture_choice)

            select_profile(["default", "production"], current="default")

            # Check that current profile has "(current)" suffix
            titles = [c["title"] for c in choices_created]
            assert "default (current)" in titles
            assert "production" in titles


class TestSelectProfileType:
    """Tests for select_profile_type function."""

    def test_select_iam_type(self):
        """Test selecting IAM profile type."""
        with patch("awsp.ui.prompts.questionary") as mock_q:
            mock_select = MagicMock()
            mock_select.ask.return_value = ProfileType.IAM
            mock_q.select.return_value = mock_select
            mock_q.Choice = MagicMock(side_effect=lambda title, value: {"title": title, "value": value})

            result = select_profile_type()

            assert result == ProfileType.IAM

    def test_select_sso_type(self):
        """Test selecting SSO profile type."""
        with patch("awsp.ui.prompts.questionary") as mock_q:
            mock_select = MagicMock()
            mock_select.ask.return_value = ProfileType.SSO
            mock_q.select.return_value = mock_select
            mock_q.Choice = MagicMock(side_effect=lambda title, value: {"title": title, "value": value})

            result = select_profile_type()

            assert result == ProfileType.SSO

    def test_select_type_cancelled(self):
        """Test cancelled type selection returns None."""
        with patch("awsp.ui.prompts.questionary") as mock_q:
            mock_select = MagicMock()
            mock_select.ask.return_value = None
            mock_q.select.return_value = mock_select
            mock_q.Choice = MagicMock(side_effect=lambda title, value: {"title": title, "value": value})

            result = select_profile_type()

            assert result is None


class TestPromptIAMProfile:
    """Tests for prompt_iam_profile function."""

    def test_prompt_iam_profile_success(self):
        """Test successful IAM profile prompt."""
        with patch("awsp.ui.prompts.questionary") as mock_q:
            # Create mock for text prompts
            def mock_text(prompt, **kwargs):
                mock = MagicMock()
                if "Profile name" in prompt:
                    mock.ask.return_value = "test-profile"
                elif "Access Key" in prompt:
                    mock.ask.return_value = "AKIAIOSFODNN7EXAMPLE"
                elif "region" in prompt.lower():
                    mock.ask.return_value = "us-west-2"
                return mock

            def mock_password(prompt, **kwargs):
                mock = MagicMock()
                mock.ask.return_value = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
                return mock

            mock_q.text = MagicMock(side_effect=mock_text)
            mock_q.password = MagicMock(side_effect=mock_password)

            result = prompt_iam_profile()

            assert result is not None
            assert result.name == "test-profile"
            assert result.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
            assert result.aws_secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
            assert result.region == "us-west-2"

    def test_prompt_iam_profile_no_region(self):
        """Test IAM profile prompt with no region."""
        with patch("awsp.ui.prompts.questionary") as mock_q:
            def mock_text(prompt, **kwargs):
                mock = MagicMock()
                if "Profile name" in prompt:
                    mock.ask.return_value = "test-profile"
                elif "Access Key" in prompt:
                    mock.ask.return_value = "AKIAIOSFODNN7EXAMPLE"
                elif "region" in prompt.lower():
                    mock.ask.return_value = ""  # Empty region
                return mock

            def mock_password(prompt, **kwargs):
                mock = MagicMock()
                mock.ask.return_value = "secretkey12345678901234567890"
                return mock

            mock_q.text = MagicMock(side_effect=mock_text)
            mock_q.password = MagicMock(side_effect=mock_password)

            result = prompt_iam_profile()

            assert result is not None
            assert result.region is None

    def test_prompt_iam_profile_cancelled_at_name(self):
        """Test cancelling at profile name prompt."""
        with patch("awsp.ui.prompts.questionary") as mock_q:
            mock_text = MagicMock()
            mock_text.ask.return_value = None  # Cancelled
            mock_q.text.return_value = mock_text

            result = prompt_iam_profile()

            assert result is None

    def test_prompt_iam_profile_cancelled_at_access_key(self):
        """Test cancelling at access key prompt."""
        with patch("awsp.ui.prompts.questionary") as mock_q:
            call_count = [0]

            def mock_text(prompt, **kwargs):
                mock = MagicMock()
                call_count[0] += 1
                if call_count[0] == 1:  # Profile name
                    mock.ask.return_value = "test"
                else:  # Access key - cancelled
                    mock.ask.return_value = None
                return mock

            mock_q.text = MagicMock(side_effect=mock_text)

            result = prompt_iam_profile()

            assert result is None

    def test_prompt_iam_profile_cancelled_at_secret_key(self):
        """Test cancelling at secret key prompt."""
        with patch("awsp.ui.prompts.questionary") as mock_q:
            def mock_text(prompt, **kwargs):
                mock = MagicMock()
                if "Profile name" in prompt:
                    mock.ask.return_value = "test"
                elif "Access Key" in prompt:
                    mock.ask.return_value = "AKIAIOSFODNN7EXAMPLE"
                return mock

            mock_password = MagicMock()
            mock_password.ask.return_value = None  # Cancelled

            mock_q.text = MagicMock(side_effect=mock_text)
            mock_q.password.return_value = mock_password

            result = prompt_iam_profile()

            assert result is None

    def test_prompt_iam_profile_with_existing_name(self):
        """Test IAM profile prompt with existing name as default."""
        with patch("awsp.ui.prompts.questionary") as mock_q:
            captured_defaults = []

            def mock_text(prompt, default="", **kwargs):
                captured_defaults.append(default)
                mock = MagicMock()
                mock.ask.return_value = "existing-profile"
                return mock

            def mock_password(prompt, **kwargs):
                mock = MagicMock()
                mock.ask.return_value = "secretkey12345678901234567890"
                return mock

            mock_q.text = MagicMock(side_effect=mock_text)
            mock_q.password = MagicMock(side_effect=mock_password)

            prompt_iam_profile(existing_name="existing-profile")

            # First call should have the existing name as default
            assert captured_defaults[0] == "existing-profile"


class TestPromptSSOProfile:
    """Tests for prompt_sso_profile function."""

    def test_prompt_sso_profile_success(self):
        """Test successful SSO profile prompt."""
        with patch("awsp.ui.prompts.questionary") as mock_q:
            responses = iter([
                "sso-test",                              # Profile name
                "https://example.awsapps.com/start",     # SSO URL
                "us-east-1",                             # SSO region
                "123456789012",                          # Account ID
                "AdministratorAccess",                   # Role name
                "us-west-2",                             # Region
            ])

            def mock_text(prompt, **kwargs):
                mock = MagicMock()
                mock.ask.return_value = next(responses)
                return mock

            mock_q.text = MagicMock(side_effect=mock_text)

            result = prompt_sso_profile()

            assert result is not None
            assert result.name == "sso-test"
            assert result.sso_start_url == "https://example.awsapps.com/start"
            assert result.sso_region == "us-east-1"
            assert result.sso_account_id == "123456789012"
            assert result.sso_role_name == "AdministratorAccess"
            assert result.region == "us-west-2"

    def test_prompt_sso_profile_cancelled(self):
        """Test cancelling SSO profile prompt."""
        with patch("awsp.ui.prompts.questionary") as mock_q:
            mock_text = MagicMock()
            mock_text.ask.return_value = None
            mock_q.text.return_value = mock_text

            result = prompt_sso_profile()

            assert result is None

    def test_prompt_sso_profile_cancelled_at_url(self):
        """Test cancelling at SSO URL prompt."""
        with patch("awsp.ui.prompts.questionary") as mock_q:
            call_count = [0]

            def mock_text(prompt, **kwargs):
                mock = MagicMock()
                call_count[0] += 1
                if call_count[0] == 1:  # Profile name
                    mock.ask.return_value = "test"
                else:  # SSO URL - cancelled
                    mock.ask.return_value = None
                return mock

            mock_q.text = MagicMock(side_effect=mock_text)

            result = prompt_sso_profile()

            assert result is None

    def test_prompt_sso_profile_no_region(self):
        """Test SSO profile with no optional region."""
        with patch("awsp.ui.prompts.questionary") as mock_q:
            responses = iter([
                "sso-test",
                "https://example.awsapps.com/start",
                "us-east-1",
                "123456789012",
                "Admin",
                "",  # Empty region
            ])

            def mock_text(prompt, **kwargs):
                mock = MagicMock()
                mock.ask.return_value = next(responses)
                return mock

            mock_q.text = MagicMock(side_effect=mock_text)

            result = prompt_sso_profile()

            assert result is not None
            assert result.region is None


class TestConfirmAction:
    """Tests for confirm_action function."""

    def test_confirm_action_yes(self):
        """Test confirming an action."""
        with patch("awsp.ui.prompts.questionary") as mock_q:
            mock_confirm = MagicMock()
            mock_confirm.ask.return_value = True
            mock_q.confirm.return_value = mock_confirm

            result = confirm_action("Delete this?")

            assert result is True
            mock_q.confirm.assert_called_once()

    def test_confirm_action_no(self):
        """Test declining an action."""
        with patch("awsp.ui.prompts.questionary") as mock_q:
            mock_confirm = MagicMock()
            mock_confirm.ask.return_value = False
            mock_q.confirm.return_value = mock_confirm

            result = confirm_action("Delete this?")

            assert result is False

    def test_confirm_action_cancelled(self):
        """Test cancelled confirmation returns False."""
        with patch("awsp.ui.prompts.questionary") as mock_q:
            mock_confirm = MagicMock()
            mock_confirm.ask.return_value = None  # Cancelled
            mock_q.confirm.return_value = mock_confirm

            result = confirm_action("Delete this?")

            assert result is False

    def test_confirm_action_default_false(self):
        """Test confirm action has default=False."""
        with patch("awsp.ui.prompts.questionary") as mock_q:
            mock_confirm = MagicMock()
            mock_confirm.ask.return_value = True
            mock_q.confirm.return_value = mock_confirm

            confirm_action("Delete?", default=False)

            # Check that default=False was passed
            call_kwargs = mock_q.confirm.call_args[1]
            assert call_kwargs.get("default") is False
