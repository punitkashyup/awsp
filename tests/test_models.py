"""Tests for config models."""

import pytest

from awsp.config.models import IAMProfile, SSOProfile, ProfileInfo, ProfileType


class TestIAMProfile:
    """Tests for IAMProfile dataclass."""

    def test_create_iam_profile(self):
        """Test creating an IAM profile."""
        profile = IAMProfile(
            name="test-profile",
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )

        assert profile.name == "test-profile"
        assert profile.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert profile.aws_secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert profile.region is None
        assert profile.output is None
        assert profile.profile_type == ProfileType.IAM

    def test_iam_profile_with_region(self):
        """Test IAM profile with region and output."""
        profile = IAMProfile(
            name="test",
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="secret",
            region="us-west-2",
            output="json",
        )

        assert profile.region == "us-west-2"
        assert profile.output == "json"

    def test_mask_secret_key(self):
        """Test secret key masking."""
        profile = IAMProfile(
            name="test",
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )

        masked = profile.mask_secret_key()
        assert masked.startswith("wJal")
        assert masked.endswith("EKEY")
        assert "*" in masked

    def test_mask_short_secret_key(self):
        """Test masking a short secret key."""
        profile = IAMProfile(
            name="test",
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="short",
        )

        masked = profile.mask_secret_key()
        assert masked == "****"

    def test_mask_access_key(self):
        """Test access key masking."""
        profile = IAMProfile(
            name="test",
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="secret",
        )

        masked = profile.mask_access_key()
        assert masked.startswith("AKIA")
        assert masked.endswith("MPLE")
        assert "*" in masked


class TestSSOProfile:
    """Tests for SSOProfile dataclass."""

    def test_create_sso_profile(self):
        """Test creating an SSO profile."""
        profile = SSOProfile(
            name="sso-test",
            sso_start_url="https://my-company.awsapps.com/start",
            sso_region="us-east-1",
            sso_account_id="123456789012",
            sso_role_name="AdministratorAccess",
        )

        assert profile.name == "sso-test"
        assert profile.sso_start_url == "https://my-company.awsapps.com/start"
        assert profile.sso_region == "us-east-1"
        assert profile.sso_account_id == "123456789012"
        assert profile.sso_role_name == "AdministratorAccess"
        assert profile.region is None
        assert profile.sso_session is None
        assert profile.profile_type == ProfileType.SSO

    def test_sso_profile_with_all_fields(self):
        """Test SSO profile with all optional fields."""
        profile = SSOProfile(
            name="sso-test",
            sso_start_url="https://my-company.awsapps.com/start",
            sso_region="us-east-1",
            sso_account_id="123456789012",
            sso_role_name="AdministratorAccess",
            region="us-west-2",
            output="table",
            sso_session="my-session",
        )

        assert profile.region == "us-west-2"
        assert profile.output == "table"
        assert profile.sso_session == "my-session"


class TestProfileInfo:
    """Tests for ProfileInfo dataclass."""

    def test_create_profile_info(self):
        """Test creating ProfileInfo."""
        info = ProfileInfo(
            name="test",
            profile_type=ProfileType.IAM,
        )

        assert info.name == "test"
        assert info.profile_type == ProfileType.IAM
        assert info.region is None
        assert info.is_current is False
        assert info.has_credentials is False
        assert info.has_config is False

    def test_profile_info_with_iam_profile(self):
        """Test ProfileInfo with attached IAM profile."""
        iam = IAMProfile(
            name="test",
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="secret",
        )

        info = ProfileInfo(
            name="test",
            profile_type=ProfileType.IAM,
            has_credentials=True,
            iam_profile=iam,
        )

        assert info.has_credentials is True
        assert info.iam_profile is not None
        assert info.iam_profile.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"

    def test_profile_info_current(self):
        """Test ProfileInfo with current flag."""
        info = ProfileInfo(
            name="active",
            profile_type=ProfileType.IAM,
            is_current=True,
        )

        assert info.is_current is True


class TestProfileType:
    """Tests for ProfileType enum."""

    def test_profile_type_values(self):
        """Test ProfileType enum values."""
        assert ProfileType.IAM.value == "iam"
        assert ProfileType.SSO.value == "sso"

    def test_profile_type_from_string(self):
        """Test creating ProfileType from string."""
        assert ProfileType("iam") == ProfileType.IAM
        assert ProfileType("sso") == ProfileType.SSO

    def test_profile_type_invalid(self):
        """Test invalid ProfileType raises error."""
        with pytest.raises(ValueError):
            ProfileType("invalid")
