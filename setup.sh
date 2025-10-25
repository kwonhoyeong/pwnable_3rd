#!/bin/bash

#######################################
# NPM Supply Chain CVE/EPSS Pipeline
# Development Environment Setup Script
# For Ubuntu 22.04 AMD64
#
# Usage:
#   ./setup.sh                    # Interactive mode
#   FORCE_YES=1 ./setup.sh        # Skip OS version prompts
#   FORCE_VENV=1 ./setup.sh       # Force recreate Python venv
#
# What this script does:
#   - Install Python 3.11, Node.js 18, Docker
#   - Setup Python virtual environment
#   - Install project dependencies
#   - Create .env file from template
#   - Start PostgreSQL and Redis containers
#######################################

set -e  # Exit on error
set -o pipefail  # Catch errors in pipes
set -u  # Error on undefined variables

# Environment variables
FORCE_YES="${FORCE_YES:-0}"  # Set FORCE_YES=1 to skip interactive prompts
FORCE_VENV="${FORCE_VENV:-0}"  # Set FORCE_VENV=1 to force recreate .venv

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on Ubuntu 22.04
check_os() {
    log_info "Checking OS version..."
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        if [ "$ID" != "ubuntu" ] || [ "$VERSION_ID" != "22.04" ]; then
            log_warning "This script is designed for Ubuntu 22.04. Your system: $ID $VERSION_ID"
            if [ "$FORCE_YES" != "1" ]; then
                read -p "Continue anyway? (y/n) " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    log_error "Setup cancelled."
                    exit 1
                fi
            else
                log_warning "FORCE_YES is set, continuing anyway..."
            fi
        else
            log_success "Running on Ubuntu 22.04"
        fi
    else
        log_error "Cannot detect OS version"
        exit 1
    fi
}

# Update system
update_system() {
    log_info "Updating system packages..."
    sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
    sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -qq
    log_success "System updated"
}

# Install basic tools
install_basic_tools() {
    log_info "Installing basic development tools..."
    sudo apt-get install -y -qq \
        git \
        curl \
        wget \
        build-essential \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release \
        unzip
    log_success "Basic tools installed"
}

# Install Python 3.11
install_python() {
    log_info "Checking Python 3.11 installation..."

    if command -v python3.11 &> /dev/null; then
        log_success "Python 3.11 already installed: $(python3.11 --version)"
        return 0
    fi

    log_info "Installing Python 3.11..."
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt-get update -qq
    sudo apt-get install -y -qq \
        python3.11 \
        python3.11-venv \
        python3.11-dev \
        python3-pip

    log_success "Python 3.11 installed: $(python3.11 --version)"
}

# Install Node.js 18 LTS
install_nodejs() {
    log_info "Checking Node.js installation..."

    if command -v node &> /dev/null; then
        NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
        if [ "$NODE_VERSION" -ge 18 ]; then
            log_success "Node.js already installed: $(node -v)"
            return 0
        else
            log_warning "Node.js version is too old: $(node -v). Installing Node.js 18..."
        fi
    fi

    log_info "Installing Node.js 18 LTS..."
    log_warning "Downloading setup script from NodeSource (this is a known supply-chain risk)"

    # Download setup script to temp file
    local setup_script=$(mktemp)
    if ! curl -fsSL https://deb.nodesource.com/setup_18.x -o "$setup_script"; then
        log_error "Failed to download NodeSource setup script"
        rm -f "$setup_script"
        exit 1
    fi

    # Run the setup script
    sudo -E bash "$setup_script"
    rm -f "$setup_script"

    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nodejs

    log_success "Node.js installed: $(node -v)"
    log_success "npm installed: $(npm -v)"
}

# Install Docker
install_docker() {
    log_info "Checking Docker installation..."

    if command -v docker &> /dev/null; then
        log_success "Docker already installed: $(docker --version)"
    else
        log_info "Installing Docker..."

        # Add Docker's official GPG key
        sudo install -m 0755 -d /etc/apt/keyrings

        # Download GPG key to temp file first
        local gpg_key=$(mktemp)
        if ! curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o "$gpg_key"; then
            log_error "Failed to download Docker GPG key"
            rm -f "$gpg_key"
            exit 1
        fi

        sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg < "$gpg_key"
        sudo chmod a+r /etc/apt/keyrings/docker.gpg
        rm -f "$gpg_key"

        # Set up Docker repository
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
          $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
          sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

        sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
            docker-ce \
            docker-ce-cli \
            containerd.io \
            docker-buildx-plugin \
            docker-compose-plugin

        # Add current user to docker group (handle sudo case)
        local target_user="${SUDO_USER:-$USER}"
        if [ "$target_user" = "root" ]; then
            log_warning "Running as root user. Skipping docker group assignment."
            log_warning "If needed, manually run: usermod -aG docker YOUR_USERNAME"
        else
            sudo usermod -aG docker "$target_user"
            log_success "Added user '$target_user' to docker group"
            log_warning "You need to log out and log back in for docker group changes to take effect"
        fi

        log_success "Docker installed: $(docker --version)"
    fi

    # Check Docker Compose
    if docker compose version &> /dev/null; then
        log_success "Docker Compose plugin installed: $(docker compose version)"
    else
        log_error "Docker Compose plugin not found"
        exit 1
    fi
}

# Setup Python virtual environment
setup_python_venv() {
    log_info "Setting up Python virtual environment..."

    if [ -d ".venv" ]; then
        if [ "$FORCE_VENV" = "1" ]; then
            log_warning "FORCE_VENV is set. Removing and recreating virtual environment..."
            rm -rf .venv
        else
            log_success "Virtual environment already exists. Reusing it."
            log_info "Set FORCE_VENV=1 to force recreation."
            source .venv/bin/activate
            # Upgrade pip
            pip install --upgrade pip -q
            return 0
        fi
    fi

    python3.11 -m venv .venv
    source .venv/bin/activate

    # Upgrade pip
    pip install --upgrade pip -q

    log_success "Python virtual environment created"
}

# Install Python dependencies
install_python_deps() {
    log_info "Installing Python dependencies..."

    if [ ! -f "requirements.txt" ]; then
        log_error "requirements.txt not found!"
        exit 1
    fi

    source .venv/bin/activate
    pip install -r requirements.txt -q

    log_success "Python dependencies installed"
}

# Install Node.js dependencies
install_nodejs_deps() {
    log_info "Installing Node.js dependencies for web frontend..."

    if [ -d "web_frontend" ]; then
        cd web_frontend

        if [ -f "package.json" ]; then
            npm install --silent
            log_success "Node.js dependencies installed"
        else
            log_warning "web_frontend/package.json not found, skipping npm install"
        fi

        cd ..
    else
        log_warning "web_frontend directory not found, skipping npm install"
    fi
}

# Setup environment file
setup_env_file() {
    log_info "Setting up environment file..."

    if [ -f ".env" ]; then
        log_warning ".env file already exists. Skipping..."
        # Ensure proper permissions even if file exists
        chmod 600 .env
        return 0
    fi

    if [ ! -f ".env.example" ]; then
        log_error ".env.example not found!"
        exit 1
    fi

    cp .env.example .env
    chmod 600 .env  # Protect secrets from other users
    log_success ".env file created from .env.example (permissions: 600)"
    log_warning "Please edit .env file to add your API keys and configuration"
}

# Start infrastructure services
start_infrastructure() {
    log_info "Starting infrastructure services (PostgreSQL, Redis)..."

    # Check if docker-compose.yml exists
    if [ ! -f "docker-compose.yml" ]; then
        log_error "docker-compose.yml not found in current directory!"
        return 1
    fi

    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker first."
        log_info "If you just installed Docker, you may need to log out and log back in."
        return 1
    fi

    # Start only database and cache services
    if ! docker compose up -d postgres redis; then
        log_error "Failed to start infrastructure services"
        log_info "Check docker-compose.yml and docker logs for details"
        return 1
    fi

    log_success "Infrastructure services started"
    log_info "PostgreSQL is running on port 5432"
    log_info "Redis is running on port 6379"
}

# Initialize database
init_database() {
    log_info "Waiting for PostgreSQL to be ready..."

    # Wait for PostgreSQL to be healthy
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker compose exec -T postgres pg_isready -U ntuser -d threatdb &> /dev/null; then
            log_success "PostgreSQL is ready"
            return 0
        fi

        log_info "Waiting for PostgreSQL... (attempt $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done

    log_error "PostgreSQL failed to start within the timeout period"
    return 1
}

# Print usage instructions
print_usage() {
    echo ""
    echo "=========================================="
    echo "  Setup Complete!"
    echo "=========================================="
    echo ""
    echo "To start developing:"
    echo ""
    echo "1. Activate Python virtual environment:"
    echo "   ${GREEN}source .venv/bin/activate${NC}"
    echo ""
    echo "2. Edit .env file with your API keys:"
    echo "   ${GREEN}nano .env${NC}"
    echo ""
    echo "3. Run the pipeline:"
    echo "   ${GREEN}python main.py --package lodash${NC}"
    echo ""
    echo "4. Start all services with Docker Compose:"
    echo "   ${GREEN}docker compose up -d${NC}"
    echo ""
    echo "5. View logs:"
    echo "   ${GREEN}docker compose logs -f${NC}"
    echo ""
    echo "6. Stop services:"
    echo "   ${GREEN}docker compose down${NC}"
    echo ""
    echo "Service URLs:"
    echo "  - Mapping Collector: http://localhost:8000"
    echo "  - EPSS Fetcher: http://localhost:8001"
    echo "  - Threat Agent: http://localhost:8002"
    echo "  - Analyzer: http://localhost:8003"
    echo "  - Query API: http://localhost:8004"
    echo "  - Web Frontend: http://localhost:5173"
    echo ""
    echo "=========================================="
}

# Main setup function
main() {
    echo ""
    echo "=========================================="
    echo "  NPM Supply Chain Security Pipeline"
    echo "  Development Environment Setup"
    echo "=========================================="
    echo ""

    check_os
    update_system
    install_basic_tools
    install_python
    install_nodejs
    install_docker
    setup_python_venv
    install_python_deps
    install_nodejs_deps
    setup_env_file

    # Try to start infrastructure (may fail if user needs to re-login for docker group)
    if start_infrastructure; then
        init_database
    else
        log_warning "Skipping infrastructure startup. You may need to log out and log back in."
    fi

    print_usage

    log_success "Setup completed successfully!"
}

# Run main function
main "$@"
