"""Data models for AWS profiles."""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class ProfileType(str, Enum):
    """Type of AWS profile."""
    IAM = "iam"
    SSO = "sso"


@dataclass
class IAMProfile:
    """IAM-based AWS profile with access key credentials."""
    name: str
    aws_access_key_id: str
    aws_secret_access_key: str
    region: Optional[str] = None
    output: Optional[str] = None

    @property
    def profile_type(self) -> ProfileType:
        return ProfileType.IAM

    def mask_secret_key(self) -> str:
        """Return masked secret key for display."""
        key = self.aws_secret_access_key
        if len(key) <= 8:
            return "****"
        return key[:4] + "*" * (len(key) - 8) + key[-4:]

    def mask_access_key(self) -> str:
        """Return masked access key for display."""
        key = self.aws_access_key_id
        if len(key) <= 8:
            return "****"
        return key[:4] + "*" * (len(key) - 8) + key[-4:]


@dataclass
class SSOProfile:
    """SSO-based AWS profile."""
    name: str
    sso_start_url: str
    sso_region: str
    sso_account_id: str
    sso_role_name: str
    region: Optional[str] = None
    output: Optional[str] = None
    sso_session: Optional[str] = None

    @property
    def profile_type(self) -> ProfileType:
        return ProfileType.SSO


@dataclass
class ProfileInfo:
    """Summary information about an AWS profile."""
    name: str
    profile_type: ProfileType
    region: Optional[str] = None
    is_current: bool = False
    has_credentials: bool = False
    has_config: bool = False
    sso_account_id: Optional[str] = None

    # Store the full profile data for operations
    iam_profile: Optional[IAMProfile] = field(default=None, repr=False)
    sso_profile: Optional[SSOProfile] = field(default=None, repr=False)
