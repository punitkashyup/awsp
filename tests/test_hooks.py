"""Tests for shell hooks."""

import pytest

from awsp.shell.hooks import (
    ShellType,
    get_export_command,
    get_unset_command,
    get_shell_hook,
    detect_shell,
)


class TestShellType:
    """Tests for ShellType enum."""

    def test_shell_type_values(self):
        """Test ShellType enum values."""
        assert ShellType.BASH.value == "bash"
        assert ShellType.ZSH.value == "zsh"
        assert ShellType.FISH.value == "fish"
        assert ShellType.POWERSHELL.value == "powershell"

    def test_shell_type_from_string(self):
        """Test creating ShellType from string."""
        assert ShellType("bash") == ShellType.BASH
        assert ShellType("zsh") == ShellType.ZSH
        assert ShellType("fish") == ShellType.FISH
        assert ShellType("powershell") == ShellType.POWERSHELL


class TestExportCommands:
    """Tests for export command generation."""

    def test_get_export_command(self):
        """Test generating export command."""
        cmd = get_export_command("production")
        assert cmd == 'export AWS_PROFILE="production"'

    def test_get_export_command_with_special_chars(self):
        """Test export command with special characters in profile name."""
        cmd = get_export_command("my-test_profile")
        assert cmd == 'export AWS_PROFILE="my-test_profile"'

    def test_get_unset_command(self):
        """Test generating unset command."""
        cmd = get_unset_command()
        assert cmd == "unset AWS_PROFILE"


class TestGetShellHook:
    """Tests for shell hook generation."""

    def test_bash_hook(self):
        """Test bash shell hook generation."""
        hook = get_shell_hook(ShellType.BASH)

        # Should contain key elements
        assert "awsp()" in hook
        assert "eval" in hook
        assert "--shell-mode" in hook
        assert "export AWS_PROFILE" in hook or "command awsp" in hook

    def test_zsh_hook(self):
        """Test zsh shell hook generation."""
        hook = get_shell_hook(ShellType.ZSH)

        # Zsh uses same hook as bash
        assert "awsp()" in hook
        assert "eval" in hook
        assert "--shell-mode" in hook

    def test_fish_hook(self):
        """Test fish shell hook generation."""
        hook = get_shell_hook(ShellType.FISH)

        # Fish has different syntax
        assert "function awsp" in hook
        assert "set -gx AWS_PROFILE" in hook
        assert "--shell-mode" in hook

    def test_bash_hook_has_comments(self):
        """Test bash hook has helpful comments."""
        hook = get_shell_hook(ShellType.BASH)

        assert "#" in hook  # Has comments
        assert "bashrc" in hook.lower() or "zshrc" in hook.lower()

    def test_fish_hook_has_comments(self):
        """Test fish hook has helpful comments."""
        hook = get_shell_hook(ShellType.FISH)

        assert "#" in hook  # Has comments
        assert "config.fish" in hook.lower()

    def test_powershell_hook(self):
        """Test PowerShell hook generation."""
        hook = get_shell_hook(ShellType.POWERSHELL)

        # PowerShell has different syntax
        assert "function awsp" in hook
        assert "$env:AWS_PROFILE" in hook
        assert "--shell-mode" in hook
        assert "Invoke-Expression" in hook or "$PROFILE" in hook

    def test_powershell_hook_has_comments(self):
        """Test PowerShell hook has helpful comments."""
        hook = get_shell_hook(ShellType.POWERSHELL)

        assert "#" in hook  # Has comments
        assert "$PROFILE" in hook


class TestDetectShell:
    """Tests for shell detection."""

    def test_detect_bash(self, monkeypatch: pytest.MonkeyPatch):
        """Test detecting bash shell."""
        monkeypatch.setenv("SHELL", "/bin/bash")
        assert detect_shell() == ShellType.BASH

    def test_detect_zsh(self, monkeypatch: pytest.MonkeyPatch):
        """Test detecting zsh shell."""
        monkeypatch.setenv("SHELL", "/bin/zsh")
        assert detect_shell() == ShellType.ZSH

    def test_detect_fish(self, monkeypatch: pytest.MonkeyPatch):
        """Test detecting fish shell."""
        monkeypatch.setenv("SHELL", "/usr/local/bin/fish")
        assert detect_shell() == ShellType.FISH

    def test_detect_unknown(self, monkeypatch: pytest.MonkeyPatch):
        """Test detecting unknown shell returns None."""
        monkeypatch.setenv("SHELL", "/bin/csh")
        assert detect_shell() is None

    def test_detect_no_shell_env(self, monkeypatch: pytest.MonkeyPatch):
        """Test when SHELL env var is not set."""
        monkeypatch.delenv("SHELL", raising=False)
        assert detect_shell() is None

    def test_detect_shell_with_version(self, monkeypatch: pytest.MonkeyPatch):
        """Test detecting shell with version in path."""
        monkeypatch.setenv("SHELL", "/usr/local/bin/zsh-5.8")
        # Should still detect zsh
        assert detect_shell() == ShellType.ZSH

    def test_detect_powershell_on_windows(self, monkeypatch: pytest.MonkeyPatch):
        """Test detecting PowerShell on Windows."""
        import sys
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setenv("PSModulePath", "C:\\Program Files\\WindowsPowerShell\\Modules")
        assert detect_shell() == ShellType.POWERSHELL

    def test_detect_powershell_windows_default(self, monkeypatch: pytest.MonkeyPatch):
        """Test Windows defaults to PowerShell."""
        import sys
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.delenv("PSModulePath", raising=False)
        monkeypatch.delenv("SHELL", raising=False)
        assert detect_shell() == ShellType.POWERSHELL
