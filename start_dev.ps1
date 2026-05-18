param(
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: .\start_dev.ps1"
    Write-Host "Starts the FastAPI backend and Next.js frontend in separate PowerShell windows."
    Write-Host "NOTE: Redis and Celery are no longer required for local TTS generation."
    exit
}

Write-Host "Starting Aria Appeal Development Environment..." -ForegroundColor Green

# Start FastAPI Backend
Write-Host "Starting FastAPI Backend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit -Command `"cd backend; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload`""


# Start Next.js Frontend
Write-Host "Starting Next.js Frontend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit -Command `"cd frontend; npm run dev`""

Write-Host "All services have been started in separate windows!" -ForegroundColor Green
Write-Host "To stop the environment, simply close the newly opened PowerShell windows." -ForegroundColor Yellow
