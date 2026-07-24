param(
    [string]$GrafanaUrl = "http://localhost:3000",
    [string]$Username = "admin",
    [string]$Password = $env:GRAFANA_ADMIN_PASSWORD,
    [string]$WebhookUrl = "http://incident-service:8086/api/incidents/alerts"
)

if ([string]::IsNullOrWhiteSpace($Password)) {
    throw "Set GRAFANA_ADMIN_PASSWORD before running this script, or pass -Password explicitly."
}

$authBytes = [Text.Encoding]::ASCII.GetBytes("$Username`:$Password")
$headers = @{
    Authorization = "Basic " + [Convert]::ToBase64String($authBytes)
}

function Invoke-GrafanaJson {
    param(
        [string]$Method,
        [string]$Path,
        [object]$Body = $null
    )

    $request = @{
        Method = $Method
        Uri = "$GrafanaUrl$Path"
        Headers = $headers
        ContentType = "application/json"
    }

    if ($null -ne $Body) {
        $request.Body = $Body | ConvertTo-Json -Depth 30 -Compress
    }

    Invoke-RestMethod @request
}

function Get-OrCreateFolderUid {
    $folders = Invoke-GrafanaJson -Method Get -Path "/api/folders"
    $existing = $folders | Where-Object { $_.title -eq "Incident Service" }
    if ($existing) {
        return $existing.uid
    }

    return (Invoke-GrafanaJson -Method Post -Path "/api/folders" -Body @{ title = "Incident Service" }).uid
}

function Get-OrCreateContactPoint {
    $contactPoints = Invoke-GrafanaJson -Method Get -Path "/api/v1/provisioning/contact-points"
    $existing = $contactPoints | Where-Object { $_.name -eq "Incident Service Webhook" -and $_.type -eq "webhook" }
    if ($existing) {
        return $existing.uid
    }

    $body = @{
        name = "Incident Service Webhook"
        type = "webhook"
        settings = @{
            url = $WebhookUrl
            httpMethod = "POST"
        }
        disableResolveMessage = $false
    }

    return (Invoke-GrafanaJson -Method Post -Path "/api/v1/provisioning/contact-points" -Body $body).uid
}

function Ensure-Policies {
    $body = @{
        receiver = "grafana-default-email"
        group_by = @("grafana_folder", "alertname")
        routes = @(
            @{
                receiver = "Incident Service Webhook"
                object_matchers = @(
                    @("team", "=", "incident-service")
                )
            }
        )
    }

    Invoke-GrafanaJson -Method Put -Path "/api/v1/provisioning/policies" -Body $body | Out-Null
}

function Build-RulePayload {
    param(
        [string]$FolderUid,
        [string]$Title,
        [string]$Expression,
        [string]$Summary,
        [string]$Description
    )

    return @{
        title = $Title
        ruleGroup = "incident-service-rules"
        folderUID = $FolderUid
        noDataState = "OK"
        execErrState = "Alerting"
        for = "30s"
        condition = "B"
        annotations = @{
            summary = $Summary
            description = $Description
        }
        labels = @{
            team = "incident-service"
            source = "grafana"
        }
        data = @(
            @{
                refId = "A"
                queryType = ""
                relativeTimeRange = @{
                    from = 600
                    to = 0
                }
                datasourceUid = "prometheus"
                model = @{
                    datasource = @{
                        type = "prometheus"
                        uid = "prometheus"
                    }
                    editorMode = "code"
                    expr = $Expression
                    instant = $true
                    intervalMs = 1000
                    maxDataPoints = 43200
                    range = $false
                    refId = "A"
                }
            },
            @{
                refId = "B"
                queryType = ""
                relativeTimeRange = @{
                    from = 0
                    to = 0
                }
                datasourceUid = "__expr__"
                model = @{
                    conditions = @(
                        @{
                            evaluator = @{
                                params = @(1)
                                type = "lt"
                            }
                            operator = @{
                                type = "and"
                            }
                            query = @{
                                params = @("A")
                            }
                            reducer = @{
                                params = @()
                                type = "last"
                            }
                            type = "query"
                        }
                    )
                    datasource = @{
                        type = "__expr__"
                        uid = "__expr__"
                    }
                    expression = "A"
                    intervalMs = 1000
                    maxDataPoints = 43200
                    refId = "B"
                    type = "threshold"
                }
            }
        )
        isPaused = $false
    }
}

function Ensure-RuleGroupInterval {
    param(
        [string]$FolderUid
    )

    $group = Invoke-GrafanaJson -Method Get -Path "/api/v1/provisioning/folder/$FolderUid/rule-groups/incident-service-rules"
    $group.interval = 10
    Invoke-GrafanaJson -Method Put -Path "/api/v1/provisioning/folder/$FolderUid/rule-groups/incident-service-rules" -Body $group | Out-Null
}

$folderUid = Get-OrCreateFolderUid
$null = Get-OrCreateContactPoint
Ensure-Policies

$existingRules = Invoke-GrafanaJson -Method Get -Path "/api/v1/provisioning/alert-rules"
$existingTitles = @{}
foreach ($rule in $existingRules) {
    $existingTitles[$rule.title] = $true
}

$rules = @(
    (Build-RulePayload -FolderUid $folderUid -Title "UserServiceDown" -Expression 'up{job="user-service"}' -Summary "User service is down" -Description "Prometheus detected user-service as unavailable"),
    (Build-RulePayload -FolderUid $folderUid -Title "PaymentServiceDown" -Expression 'up{job="payment-service"}' -Summary "Payment service is down" -Description "Prometheus detected payment-service as unavailable"),
    (Build-RulePayload -FolderUid $folderUid -Title "TransactionServiceDown" -Expression 'up{job="transaction-service"}' -Summary "Transaction service is down" -Description "Prometheus detected transaction-service as unavailable")
)

$createdRuleTitles = @()
foreach ($rule in $rules) {
    if (-not $existingTitles.ContainsKey($rule.title)) {
        Invoke-GrafanaJson -Method Post -Path "/api/v1/provisioning/alert-rules" -Body $rule | Out-Null
        $createdRuleTitles += $rule.title
    }
}

Ensure-RuleGroupInterval -FolderUid $folderUid

[pscustomobject]@{
    folderUid = $folderUid
    createdRuleTitles = $createdRuleTitles
} | ConvertTo-Json -Depth 10
