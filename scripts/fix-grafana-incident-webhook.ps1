param(
    [string]$GrafanaBaseUrl = "http://localhost:3000",
    [string]$Username = "admin",
    [string]$Password = "admin123",
    [string]$ContactPointUid = "ffqxr4x7sxkw0f",
    [string]$IncidentWebhookUrl = "http://incident-service:8086/api/incidents/alerts"
)

$pair = "$Username`:$Password"
$encoded = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($pair))
$headers = @{
    Authorization = "Basic $encoded"
    "Content-Type" = "application/json"
}

$body = @{
    uid = $ContactPointUid
    name = "Incident Service Webhook"
    type = "webhook"
    disableResolveMessage = $false
    settings = @{
        httpMethod = "POST"
        url = $IncidentWebhookUrl
    }
} | ConvertTo-Json -Depth 6

Invoke-RestMethod `
    -Method Put `
    -Headers $headers `
    -Uri "$GrafanaBaseUrl/api/v1/provisioning/contact-points/$ContactPointUid" `
    -Body $body `
    -TimeoutSec 20

Write-Host "Grafana contact point updated to $IncidentWebhookUrl"
