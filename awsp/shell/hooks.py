"""Shell integration hooks for profile switching."""

from enum import Enum
from typing import Optional


class ShellType(str, Enum):
    """Supported shell types."""
    BASH = "bash"
    ZSH = "zsh"
    FISH = "fish"


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
    if [[ -z "$cmd" ]] || [[ "$cmd" == "switch" ]]; then
        local output
        local exit_code

        # Run awsp with --shell-mode flag
        output=$(command awsp "$@" --shell-mode 2>&1)
        exit_code=$?

        if [[ $exit_code -eq 0 ]]; then
            # Output contains export command - eval it
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
    if test -z "$cmd"; or test "$cmd" = "switch"
        set -l output (command awsp $argv --shell-mode 2>&1)
        set -l exit_code $status

        if test $exit_code -eq 0
            # Parse and execute the export command
            # Fish uses 'set -gx VAR value' instead of 'export VAR=value'
            echo $output | while read -l line
                if string match -qr '^export AWS_PROFILE=' -- $line
                    set -l profile (string replace 'export AWS_PROFILE="' '' $line | string replace '"' '')
                    set -gx AWS_PROFILE $profile
                    echo "Switched to profile: $profile"
                else if string match -qr '^unset AWS_PROFILE' -- $line
                    set -e AWS_PROFILE
                    echo "AWS_PROFILE unset"
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


def detect_shell() -> Optional[ShellType]:
    """Attempt to detect the current shell type."""
    import os

    shell = os.environ.get("SHELL", "")

    if "zsh" in shell:
        return ShellType.ZSH
    elif "bash" in shell:
        return ShellType.BASH
    elif "fish" in shell:
        return ShellType.FISH

    return None
