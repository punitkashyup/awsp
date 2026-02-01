"""Pytest configuration and fixtures."""

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_aws_dir() -> Generator[Path, None, None]:
    """Create a temporary .aws directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        aws_dir = Path(tmpdir) / ".aws"
        aws_dir.mkdir()
        yield aws_dir


@pytest.fixture
def mock_aws_env(temp_aws_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set up mock AWS environment variables."""
    credentials_path = temp_aws_dir / "credentials"
    config_path = temp_aws_dir / "config"

    # Create empty files
    credentials_path.touch()
    config_path.touch()

    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(credentials_path))
    monkeypatch.setenv("AWS_CONFIG_FILE", str(config_path))
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_PROFILE", raising=False)

    return temp_aws_dir


@pytest.fixture
def sample_credentials_file(temp_aws_dir: Path) -> Path:
    """Create a sample credentials file."""
    credentials_path = temp_aws_dir / "credentials"
    credentials_path.write_text("""[default]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

[production]
aws_access_key_id = AKIAPRODEXAMPLE12345
aws_secret_access_key = prodSecretKey1234567890EXAMPLE1234

[staging]
aws_access_key_id = AKIASTAGEXAMPLE12345
aws_secret_access_key = stagSecretKey1234567890EXAMPLE1234
""")
    return credentials_path


@pytest.fixture
def sample_config_file(temp_aws_dir: Path) -> Path:
    """Create a sample config file."""
    config_path = temp_aws_dir / "config"
    config_path.write_text("""[default]
region = us-east-1
output = json

[profile production]
region = us-west-2
output = table

[profile staging]
region = eu-west-1

[profile sso-profile]
sso_start_url = https://my-company.awsapps.com/start
sso_region = us-east-1
sso_account_id = 123456789012
sso_role_name = AdministratorAccess
region = us-west-2
""")
    return config_path


@pytest.fixture
def populated_aws_env(
    temp_aws_dir: Path,
    sample_credentials_file: Path,
    sample_config_file: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Set up a fully populated mock AWS environment."""
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(sample_credentials_file))
    monkeypatch.setenv("AWS_CONFIG_FILE", str(sample_config_file))
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_PROFILE", raising=False)

    return temp_aws_dir
