# OpenEnv Pre-Submission Validator - Windows PowerShell Version

param([switch]$Verbose)

$REPO_DIR = Get-Location
$DOCKER_BUILD_TIMEOUT = 300

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  OpenEnv Pre-Submission Validator      " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Step 1/3: Checking project structure ..."

$requiredFiles = @(
    "openenv.yaml",
    "Dockerfile",
    "inference.py",
    "app.py",
    "requirements.txt"
)

$allPresent = $true
foreach ($file in $requiredFiles) {
    if (-not (Test-Path "$REPO_DIR\$file")) {
        Write-Host "❌ $file not found in repository root" -ForegroundColor Red
        $allPresent = $false
    }
}

if (-not $allPresent) {
    Write-Host "`nStopped at Step 1" -ForegroundColor Red
    exit 1
}

Write-Host "✅ All required files present" -ForegroundColor Green

Write-Host "`nStep 2/3: Running docker build ..."

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ docker command not found" -ForegroundColor Red
    Write-Host "💡 Install Docker: https://docs.docker.com/get-docker/" -ForegroundColor Yellow
    Write-Host "`nStopped at Step 2" -ForegroundColor Red
    exit 1
}

Write-Host "  Building Docker image..."

try {
    $env:DOCKER_BUILDKIT = 1
    docker build "$REPO_DIR"
    if ($LASTEXITCODE -ne 0) {
        throw "Docker build failed"
    }
    Write-Host "✅ Docker build succeeded" -ForegroundColor Green
}
catch {
    Write-Host "❌ Docker build failed" -ForegroundColor Red
    Write-Host "`nStopped at Step 2" -ForegroundColor Red
    exit 1
}

Write-Host "`nStep 3/3: Running openenv validate ..."

if (-not (Get-Command openenv -ErrorAction SilentlyContinue)) {
    Write-Host "❌ openenv command not found" -ForegroundColor Red
    Write-Host "💡 Install it: pip install openenv-core" -ForegroundColor Yellow
    Write-Host "`nStopped at Step 3" -ForegroundColor Red
    exit 1
}

try {
    openenv validate
    if ($LASTEXITCODE -ne 0) {
        throw "openenv validate failed"
    }
    Write-Host "✅ openenv validate passed" -ForegroundColor Green
}
catch {
    Write-Host "❌ openenv validate failed" -ForegroundColor Red
    Write-Host "`nStopped at Step 3" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  All 3/3 checks passed!                " -ForegroundColor Green
Write-Host "  Your submission is ready to submit.   " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

exit 0