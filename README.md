# AWSP - AWS Profile Switcher

A command-line utility for easily managing and switching between AWS CLI profiles.

## Features

- **List profiles** - View all configured AWS profiles (IAM and SSO)
- **Switch profiles** - Interactive profile selection with fuzzy search
- **Add profiles** - Create new IAM or SSO profiles interactively
- **Remove profiles** - Safely remove profiles with confirmation
- **Validate credentials** - Test AWS credentials using STS
- **Shell integration** - Seamless profile switching in bash, zsh, and fish

## Installation

### macOS / Linux

```bash
# Install pipx (if not installed)
brew install pipx    # macOS
# or: sudo apt install pipx    # Ubuntu/Debian

# Install awsp
pipx install awsp

# Set up shell integration
awsp setup
source ~/.zshrc  # or ~/.bashrc for Bash
```

### Windows

```powershell
# Install pipx (if not installed)
pip install --user pipx
pipx ensurepath

# Restart PowerShell, then install awsp
pipx install awsp

# Set up shell integration
awsp setup
. $PROFILE
```

### Alternative: pip install

```bash
pip install awsp
```

> **Note:** [pipx](https://pipx.pypa.io/) is recommended as it installs CLI tools in isolated environments.

## Quick Start

### macOS / Linux

```bash
# Add a new profile
awsp add

# Activate a profile
awsp activate my-profile

# Deactivate current profile
awsp deactivate

# List all profiles
awsp list

# Validate credentials
awsp validate
```

### Windows (PowerShell)

```powershell
# Add a new profile
awsp add

# Activate a profile
awsp activate my-profile

# Deactivate current profile
awsp deactivate

# List all profiles
awsp list

# Validate credentials
awsp validate
```

## Shell Integration

Add to your shell configuration for automatic profile switching:

**Bash** (`~/.bashrc`):
```bash
eval "$(awsp init)"
```

**Zsh** (`~/.zshrc`):
```bash
eval "$(awsp init)"
```

**Fish** (`~/.config/fish/config.fish`):
```fish
awsp init --shell fish | source
```

**PowerShell** (`$PROFILE`):
```powershell
Invoke-Expression (awsp init --shell powershell)
```

Or simply run `awsp setup` to auto-configure your shell.

## Commands

| Command | Description |
|---------|-------------|
| `awsp setup` | Auto-configure shell integration (run once) |
| `awsp activate [NAME]` | Activate a profile (sets AWS_PROFILE) |
| `awsp deactivate` | Deactivate current profile (unsets AWS_PROFILE) |
| `awsp list` | List all AWS profiles |
| `awsp add` | Add a new profile (IAM or SSO) |
| `awsp remove NAME` | Remove a profile |
| `awsp current` | Show current active profile |
| `awsp validate [NAME]` | Validate profile credentials |
| `awsp info [NAME]` | Show detailed profile info |
| `awsp init` | Output shell integration hook |
| `awsp` | Interactive profile switcher |
| `awsp switch [NAME]` | Alias for activate |

## Requirements

- Python 3.10+
- AWS CLI (for credential validation and SSO login)

## Platform Support

| Platform | Shell | Status |
|----------|-------|--------|
| macOS | Zsh, Bash, Fish | ✅ Full support |
| Linux | Bash, Zsh, Fish | ✅ Full support |
| Windows | PowerShell | ✅ Full support |

## License

MIT
