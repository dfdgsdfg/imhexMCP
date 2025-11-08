#!/bin/bash
# ImHex MCP Server Installation Script
# This script installs the MCP server and sets up Claude Desktop configuration

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect OS
detect_os() {
    case "$(uname -s)" in
        Linux*)     OS="Linux";;
        Darwin*)    OS="macOS";;
        MINGW*|MSYS*|CYGWIN*)    OS="Windows";;
        *)          OS="Unknown";;
    esac
    print_info "Detected OS: $OS"
}

# Check Python version
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    print_info "Python version: $PYTHON_VERSION"

    # Check minimum version (3.10)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
        print_error "Python 3.10 or higher is required"
        exit 1
    fi
}

# Install Python dependencies
install_dependencies() {
    print_info "Installing Python dependencies..."

    if command -v pip3 &> /dev/null; then
        pip3 install -r requirements.txt
    elif command -v pip &> /dev/null; then
        pip install -r requirements.txt
    else
        print_error "pip is not installed"
        exit 1
    fi

    print_info "Dependencies installed successfully"
}

# Install as Python package
install_package() {
    print_info "Installing MCP server as Python package..."

    if command -v pip3 &> /dev/null; then
        pip3 install -e .
    elif command -v pip &> /dev/null; then
        pip install -e .
    fi

    print_info "Package installed successfully"
}

# Test connection to ImHex
test_connection() {
    print_info "Testing connection to ImHex..."

    if python3 test_server.py; then
        print_info "Successfully connected to ImHex!"
        return 0
    else
        print_warn "Could not connect to ImHex"
        print_warn "Make sure ImHex is running and Network Interface is enabled"
        return 1
    fi
}

# Get Claude Desktop config path
get_claude_config_path() {
    case "$OS" in
        macOS)
            echo "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
            ;;
        Linux)
            echo "$HOME/.config/Claude/claude_desktop_config.json"
            ;;
        Windows)
            echo "$APPDATA/Claude/claude_desktop_config.json"
            ;;
        *)
            echo ""
            ;;
    esac
}

# Configure Claude Desktop
configure_claude() {
    print_info "Configuring Claude Desktop..."

    CLAUDE_CONFIG=$(get_claude_config_path)

    if [ -z "$CLAUDE_CONFIG" ]; then
        print_warn "Unknown OS, skipping Claude configuration"
        return 1
    fi

    # Create directory if it doesn't exist
    mkdir -p "$(dirname "$CLAUDE_CONFIG")"

    # Get absolute path to server.py
    SERVER_PATH="$(cd "$(dirname "$0")" && pwd)/server.py"

    # Check if config file exists
    if [ -f "$CLAUDE_CONFIG" ]; then
        print_warn "Claude config already exists at: $CLAUDE_CONFIG"
        read -p "Do you want to update it? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Skipping Claude configuration"
            return 0
        fi

        # Backup existing config
        cp "$CLAUDE_CONFIG" "$CLAUDE_CONFIG.backup"
        print_info "Backed up existing config to $CLAUDE_CONFIG.backup"
    fi

    # Create or update config
    cat > "$CLAUDE_CONFIG" <<EOF
{
  "mcpServers": {
    "imhex": {
      "command": "python3",
      "args": ["$SERVER_PATH"]
    }
  }
}
EOF

    print_info "Claude Desktop configured successfully"
    print_info "Config file: $CLAUDE_CONFIG"
    print_warn "Please restart Claude Desktop for changes to take effect"
}

# Main installation
main() {
    echo "================================"
    echo "ImHex MCP Server Installation"
    echo "================================"
    echo

    detect_os
    check_python

    # Change to script directory
    cd "$(dirname "$0")"

    install_dependencies

    # Optional: install as package
    read -p "Install as Python package? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_package
    fi

    # Test connection
    if test_connection; then
        echo
    else
        print_info "You can test the connection later by running: python3 test_server.py"
        echo
    fi

    # Configure Claude
    read -p "Configure Claude Desktop? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        configure_claude
    fi

    echo
    echo "================================"
    print_info "Installation complete!"
    echo "================================"
    echo
    print_info "Next steps:"
    echo "  1. Make sure ImHex is running"
    echo "  2. Enable Network Interface in ImHex (Settings → General)"
    echo "  3. Restart Claude Desktop if configured"
    echo "  4. Test by asking Claude to check ImHex capabilities"
    echo
}

# Run installation
main
