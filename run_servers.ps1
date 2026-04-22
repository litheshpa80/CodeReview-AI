$env:PYTHONPATH = $PSScriptRoot
start-process python -ArgumentList "-m uvicorn backend.main:app --port 8000" -NoNewWindow
start-process python -ArgumentList "dashboard/app.py" -NoNewWindow
Write-Output "Servers started with PYTHONPATH=$env:PYTHONPATH"
