param(
    [string]$KibanaUrl = "http://localhost:5601",
    [string]$WebhookUrl = "http://incident-service:8090/api/incidents/webhook"
)

$headers = @{ "kbn-xsrf" = "true" }

function Invoke-KibanaJson {
    param(
        [string]$Method,
        [string]$Path,
        [object]$Body = $null
    )

    $request = @{
        Method = $Method
        Uri = "$KibanaUrl$Path"
        Headers = $headers
        ContentType = "application/json"
    }

    if ($null -ne $Body) {
        $request.Body = $Body | ConvertTo-Json -Depth 20 -Compress
    }

    Invoke-RestMethod @request
}

function Test-WebhookConnectorSupport {
    try {
        $types = Invoke-KibanaJson -Method Get -Path "/api/actions/connector_types"
        $webhookType = $types | Where-Object { $_.id -eq ".webhook" }

        if ($null -eq $webhookType) {
            throw "Kibana did not return the .webhook connector type."
        }

        if (-not $webhookType.enabled) {
            throw "Kibana webhook connectors are disabled on the current license. The Elastic Basic license in this stack does not allow the .webhook action type, so the exact 'Kibana rule -> webhook -> incident-service' flow cannot be completed until the license is upgraded."
        }
    } catch {
        throw $_
    }
}

function Get-OrCreateWebhookConnector {
    $connectors = Invoke-KibanaJson -Method Get -Path "/api/actions/connectors"
    $existing = $connectors | Where-Object { $_.name -eq "Incident Service Webhook" }
    if ($existing) {
        return $existing.id
    }

    $body = @{
        name = "Incident Service Webhook"
        connector_type_id = ".webhook"
        config = @{
            method = "post"
            url = $WebhookUrl
            hasAuth = $false
            headers = @{}
        }
        secrets = @{}
    }

    return (Invoke-KibanaJson -Method Post -Path "/api/actions/connector" -Body $body).id
}

function Build-RuleAction {
    param(
        [string]$ConnectorId
    )

    return @(
        @{
            group = "query matched"
            id = $ConnectorId
            params = @{
                body = '{"source":"KIBANA","title":"{{rule.name}}","description":"{{context.message}}","service_name":"log-generator-service","severity":"HIGH","status":"OPEN","raw_payload":{"kibana":{"date":"{{date}}","group":"{{context.group}}","value":"{{context.value}}"}}}'
            }
        }
    )
}

function Build-EsQueryRule {
    param(
        [string]$Name,
        [string]$Query,
        [string]$ConnectorId
    )

    return @{
        name = $Name
        rule_type_id = ".es-query"
        consumer = "alerts"
        enabled = $true
        schedule = @{ interval = "1m" }
        notify_when = "onActionGroupChange"
        tags = @("incident-service", "kibana")
        throttle = $null
        params = @{
            searchType = "esQuery"
            timeField = "@timestamp"
            index = @("banking-logs-*")
            esQuery = "{""query"":{""bool"":{""filter"":[{""query_string"":{""query"":""$Query""}}]}}}"
            size = 0
            aggType = "count"
            groupBy = "all"
            termSize = 5
            thresholdComparator = ">"
            threshold = @(0)
            timeWindowSize = 5
            timeWindowUnit = "m"
            excludeHitsFromPreviousRun = $true
        }
        actions = Build-RuleAction -ConnectorId $ConnectorId
    }
}

Test-WebhookConnectorSupport
$connectorId = Get-OrCreateWebhookConnector

$rules = @(
    (Build-EsQueryRule -Name "Payment Timeout" -Query 'message:"PAYMENT_TIMEOUT"' -ConnectorId $connectorId),
    (Build-EsQueryRule -Name "Database Failure" -Query 'message:"Connection refused"' -ConnectorId $connectorId),
    (Build-EsQueryRule -Name "Login Failure" -Query 'message:"LOGIN_FAILED"' -ConnectorId $connectorId),
    (Build-EsQueryRule -Name "Java Exception" -Query 'message:"Exception" OR level:"ERROR"' -ConnectorId $connectorId)
)

$existingRules = Invoke-KibanaJson -Method Get -Path "/api/alerting/rules/_find?search_fields=name&search=*&per_page=100"
$existingNames = @{}
foreach ($rule in $existingRules.data) {
    $existingNames[$rule.name] = $true
}

$created = @()
foreach ($rule in $rules) {
    if (-not $existingNames.ContainsKey($rule.name)) {
        $created += Invoke-KibanaJson -Method Post -Path "/api/alerting/rule" -Body $rule
    }
}

[pscustomobject]@{
    connectorId = $connectorId
    createdRuleNames = $created | ForEach-Object { $_.name }
} | ConvertTo-Json -Depth 10
