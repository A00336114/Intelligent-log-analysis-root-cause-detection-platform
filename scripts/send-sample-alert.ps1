$body = Get-Content -Raw "$PSScriptRoot\sample-alert.json"

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8086/api/incidents/alerts" `
  -ContentType "application/json" `
  -Body $body

Write-Host ""
Write-Host "Incidents:"
Invoke-RestMethod -Method Get -Uri "http://localhost:8086/api/incidents" | ConvertTo-Json -Depth 6

Write-Host ""
Write-Host "Parsed logs:"
Invoke-RestMethod -Method Get -Uri "http://localhost:5000/parsed-logs" | ConvertTo-Json -Depth 6
