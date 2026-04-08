#!/usr/bin/env bash

set -euo pipefail

# Configuration
REPO_DIR="$(pwd)"
DOCKER_BUILD_TIMEOUT=300
NC='\033[0m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'

log() { printf "  %b%s%b\n" "$NC" "$1" "$NC"; }
pass() { printf "✅ %b%s%b\n" "$GREEN" "$1" "$NC"; }
fail() { printf "❌ %b%s%b\n" "$RED" "$1" "$NC"; }
hint() { printf "💡 %b%s%b\n" "$YELLOW" "$1" "$NC"; }
stop_at() { printf "\n%bStopped at %s%b\n" "$RED" "$1" "$NC"; exit 1; }

run_with_timeout() {
    local timeout="$1"
    shift
    if command -v timeout &>/dev/null; then
        timeout "$timeout" "$@"
    else
        "$@"
    fi
}

printf "\n"
printf "${BOLD}========================================${NC}\n"
printf "${BOLD}  OpenEnv Pre-Submission Validator${NC}\n"
printf "${BOLD}========================================${NC}\n"
printf "\n"

log "${BOLD}Step 1/3: Checking project structure${NC} ..."

if [ ! -f "$REPO_DIR/openenv.yaml" ]; then
    fail "openenv.yaml not found in repository root"
    stop_at "Step 1"
fi

if [ ! -f "$REPO_DIR/Dockerfile" ]; then
    fail "Dockerfile not found in repository root"
    stop_at "Step 1"
fi

if [ ! -f "$REPO_DIR/inference.py" ]; then
    fail "inference.py not found in repository root"
    stop_at "Step 1"
fi

if [ ! -f "$REPO_DIR/app.py" ]; then
    fail "app.py not found in repository root"
    stop_at "Step 1"
fi

if [ ! -f "$REPO_DIR/requirements.txt" ]; then
    fail "requirements.txt not found in repository root"
    stop_at "Step 1"
fi

pass "All required files present"

log "${BOLD}Step 2/3: Running docker build${NC} ..."

if ! command -v docker &>/dev/null; then
    fail "docker command not found"
    hint "Install Docker: https://docs.docker.com/get-docker/"
    stop_at "Step 2"
fi

log "  Building Docker image..."

BUILD_OK=false
BUILD_OUTPUT=$(run_with_timeout "$DOCKER_BUILD_TIMEOUT" docker build "$REPO_DIR" 2>&1) && BUILD_OK=true

if [ "$BUILD_OK" = true ]; then
    pass "Docker build succeeded"
else
    fail "Docker build failed (timeout=${DOCKER_BUILD_TIMEOUT}s)"
    printf "%s\n" "$BUILD_OUTPUT" | tail -20
    stop_at "Step 2"
fi

log "${BOLD}Step 3/3: Running openenv validate${NC} ..."

if ! command -v openenv &>/dev/null; then
    fail "openenv command not found"
    hint "Install it: pip install openenv-core"
    stop_at "Step 3"
fi

VALIDATE_OK=false
VALIDATE_OUTPUT=$(cd "$REPO_DIR" && openenv validate 2>&1) && VALIDATE_OK=true

if [ "$VALIDATE_OK" = true ]; then
    pass "openenv validate passed"
    [ -n "$VALIDATE_OUTPUT" ] && log "  $VALIDATE_OUTPUT"
else
    fail "openenv validate failed"
    printf "%s\n" "$VALIDATE_OUTPUT"
    stop_at "Step 3"
fi

printf "\n"
printf "${BOLD}========================================${NC}\n"
printf "${GREEN}${BOLD}  All 3/3 checks passed!${NC}\n"
printf "${GREEN}${BOLD}  Your submission is ready to submit.${NC}\n"
printf "${BOLD}========================================${NC}\n"
printf "\n"

exit 0