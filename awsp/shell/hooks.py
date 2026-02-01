"""Shell integration hooks for profile switching."""

from enum import Enum
from typing import Optional


class ShellType(str, Enum):
    """Supported shell types."""
    BASH = "bash"
    ZSH = "zsh"
    FISH = "fish"
    POWERSHELL = "powershell"


def get_export_command(profile_name: str) -> str:
    """Generate export command for a profile.

    This is used with --shell-mode to output commands that can be eval'd.
    """
    return f'export AWS_PROFILE="{profile_name}"'


def get_unset_command() -> str:
    """Generate command to unset AWS_PROFILE."""
    return "unset AWS_PROFILE"


def get_shell_hook(shell: ShellType) -> str:
    """Generate shell hook code for the given shell type.

    The hook creates a wrapper function that:
    1. Intercepts 'switch' and bare 'awsp' commands
    2. Evals the output to set AWS_PROFILE in the current shell
    3. Passes other commands through to the real awsp binary
    """
    if shell == ShellType.FISH:
        return _get_fish_hook()
    elif shell == ShellType.POWERSHELL:
        return _get_powershell_hook()
    else:
        return _get_bash_zsh_hook()


def _get_bash_zsh_hook() -> str:
    """Generate bash/zsh hook."""
    return '''# awsp shell integration
# Add this to your ~/.bashrc or ~/.zshrc:
#   eval "$(awsp init)"

awsp() {
    local cmd="${1:-}"

    # Commands that need shell integration (modify environment)
    if [[ -z "$cmd" ]] || [[ "$cmd" == "switch" ]] || [[ "$cmd" == "activate" ]] || [[ "$cmd" == "deactivate" ]]; then
        local output
        local exit_code

        # Run awsp with --shell-mode flag
        output=$(command awsp "$@" --shell-mode 2>&1)
        exit_code=$?

        if [[ $exit_code -eq 0 ]]; then
            # Output contains export/unset command - eval it
            eval "$output"
        else
            # Error occurred - just print the output
            echo "$output"
            return $exit_code
        fi
    else
        # Other commands - pass through directly
        command awsp "$@"
    fi
}

# Show current profile in prompt (optional)
# Uncomment to add AWS profile to your prompt:
# _awsp_prompt() {
#     if [[ -n "$AWS_PROFILE" ]]; then
#         echo "(aws:$AWS_PROFILE) "
#     fi
# }
# PS1='$(_awsp_prompt)'"$PS1"
'''


def _get_fish_hook() -> str:
    """Generate fish shell hook."""
    return '''# awsp shell integration for fish
# Add this to your ~/.config/fish/config.fish:
#   awsp init --shell fish | source

function awsp
    set -l cmd $argv[1]

    # Commands that need shell integration
    if test -z "$cmd"; or test "$cmd" = "switch"; or test "$cmd" = "activate"; or test "$cmd" = "deactivate"
        set -l output (command awsp $argv --shell-mode 2>&1)
        set -l exit_code $status

        if test $exit_code -eq 0
            # Parse and execute the export command
            # Fish uses 'set -gx VAR value' instead of 'export VAR=value'
            echo $output | while read -l line
                if string match -qr '^export AWS_PROFILE=' -- $line
                    set -l profile (string replace 'export AWS_PROFILE="' '' $line | string replace '"' '')
                    set -gx AWS_PROFILE $profile
                else if string match -qr '^unset AWS_PROFILE' -- $line
                    set -e AWS_PROFILE
                else
                    echo $line
                end
            end
        else
            echo $output
            return $exit_code
        end
    else
        command awsp $argv
    end
end

# Show current profile in prompt (optional)
# Add to your fish_prompt function:
# if set -q AWS_PROFILE
#     echo -n "(aws:$AWS_PROFILE) "
# end
'''


def _get_powershell_hook() -> str:
    """Generate PowerShell hook."""
    return '''# awsp shell integration for PowerShell
# Add this to your PowerShell profile ($PROFILE):
#   Invoke-Expression (awsp init --shell powershell)

function awsp {
    param([Parameter(ValueFromRemainingArguments=$true)]$Args)

    $cmd = if ($Args.Count -gt 0) { $Args[0] } else { "" }

    # Commands that need shell integration (modify environment)
    if ($cmd -eq "" -or $cmd -eq "switch" -or $cmd -eq "activate" -or $cmd -eq "deactivate") {
        # Find the real awsp executable
        $awspPath = (Get-Command awsp -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1).Source

        if (-not $awspPath) {
            Write-Error "awsp executable not found"
            return
        }

        # Run awsp with --shell-mode flag
        $output = & $awspPath @Args --shell-mode 2>&1

        if ($LASTEXITCODE -eq 0) {
            # Parse and execute the output
            foreach ($line in $output) {
                if ($line -match '^export AWS_PROFILE="(.+)"$') {
                    $env:AWS_PROFILE = $Matches[1]
                }
                elseif ($line -match '^unset AWS_PROFILE') {
                    Remove-Item Env:AWS_PROFILE -ErrorAction SilentlyContinue
                }
                elseif ($line -match '^echo "(.+)"$') {
                    Write-Host $Matches[1]
                }
            }
        }
        else {
            # Error occurred - just print the output
            $output | ForEach-Object { Write-Host $_ }
        }
    }
    else {
        # Other commands - pass through directly
        $awspPath = (Get-Command awsp -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1).Source
        if ($awspPath) {
            & $awspPath @Args
        }
    }
}

# Show current profile in prompt (optional)
# Add to your prompt function:
# function prompt {
#     $awsProfile = if ($env:AWS_PROFILE) { "(aws:$env:AWS_PROFILE) " } else { "" }
#     "$awsProfile$(Get-Location)> "
# }
'''


def detect_shell() -> Optional[ShellType]:
    """Attempt to detect the current shell type."""
    import os
    import sys

    # Check for Windows PowerShell
    if sys.platform == "win32":
        # On Windows, check if running in PowerShell
        if os.environ.get("PSModulePath"):
            return ShellType.POWERSHELL
        return ShellType.POWERSHELL  # Default to PowerShell on Windows

    # Unix-like systems
    shell = os.environ.get("SHELL", "")

    if "zsh" in shell:
        return ShellType.ZSH
    elif "bash" in shell:
        return ShellType.BASH
    elif "fish" in shell:
        return ShellType.FISH

    return None
