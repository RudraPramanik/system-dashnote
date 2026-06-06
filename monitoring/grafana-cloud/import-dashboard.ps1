# Import API Overview dashboard into Grafana Cloud.
# Requires in .env (repo root):
#   GRAFANA_CLOUD_STACK_URL=https://YOUR-STACK.grafana.net
#   GRAFANA_CLOUD_API_TOKEN=glsa_...  (service account token with dashboards:write)
#
# Usage:
#   .\monitoring\grafana-cloud\import-dashboard.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$EnvFile = Join-Path $Root ".env"
$DashboardFile = Join-Path $PSScriptRoot "api_overview.cloud.json"

function Read-DotEnv {
    param([string]$Path)
    $vars = @{}
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if ($line -eq "" -or $line.StartsWith("#")) { return }
        if ($line -match '^([^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $val = $matches[2].Trim().Trim('"').Trim("'")
            $vars[$key] = $val
        }
    }
    return $vars
}

if (-not (Test-Path $EnvFile)) {
    throw ".env not found at $EnvFile"
}
if (-not (Test-Path $DashboardFile)) {
    throw "Dashboard JSON not found at $DashboardFile"
}

$envVars = Read-DotEnv -Path $EnvFile
$stackUrl = $envVars["GRAFANA_CLOUD_STACK_URL"].TrimEnd("/")
$apiToken = $envVars["GRAFANA_CLOUD_API_TOKEN"]

if ([string]::IsNullOrWhiteSpace($stackUrl)) {
    throw @"
GRAFANA_CLOUD_STACK_URL is missing in .env.

Find it in Grafana Cloud:
  grafana.com -> your stack -> Grafana -> Details -> URL
  Example: https://myorg.grafana.net
"@
}
if ([string]::IsNullOrWhiteSpace($apiToken)) {
    throw @"
GRAFANA_CLOUD_API_TOKEN is missing in .env.

Create a Grafana service account token (not the metrics remote_write token):
  Grafana UI -> Administration -> Users and access -> Service accounts
  Create token with Admin or Editor role (needs dashboards:write)
  Add to .env: GRAFANA_CLOUD_API_TOKEN=glsa_...
"@
}

$headers = @{
    Authorization = "Bearer $apiToken"
    "Content-Type" = "application/json"
    Accept         = "application/json"
}

Write-Host "Checking Grafana API at $stackUrl ..."
try {
    $org = Invoke-RestMethod -Uri "$stackUrl/api/org" -Headers $headers -Method Get
    Write-Host "Connected to org: $($org.name)"
} catch {
    throw "Grafana API auth failed ($stackUrl/api/org): $($_.Exception.Message)"
}

Write-Host "Looking up Prometheus data source ..."
$datasources = Invoke-RestMethod -Uri "$stackUrl/api/datasources" -Headers $headers -Method Get
$promDs = $datasources | Where-Object { $_.type -eq "prometheus" } | Select-Object -First 1
if (-not $promDs) {
    throw "No Prometheus data source found in this Grafana stack."
}
Write-Host "Using Prometheus datasource: $($promDs.name) (uid=$($promDs.uid))"

$raw = Get-Content $DashboardFile -Raw | ConvertFrom-Json
$dashboard = $raw.PSObject.Copy()
$dashboard.PSObject.Properties.Remove("__inputs")
$dashboard.PSObject.Properties.Remove("__requires")

function Set-DatasourceUid {
    param($Node, [string]$Uid)
    if ($null -eq $Node) { return }
    if ($Node -is [System.Collections.IEnumerable] -and $Node -isnot [string]) {
        foreach ($item in $Node) { Set-DatasourceUid -Node $item -Uid $Uid }
        return
    }
    if ($Node -is [pscustomobject]) {
        if ($Node.PSObject.Properties.Name -contains "datasource") {
            $Node.datasource = [pscustomobject]@{ type = "prometheus"; uid = $Uid }
        }
        foreach ($prop in $Node.PSObject.Properties) {
            Set-DatasourceUid -Node $prop.Value -Uid $Uid
        }
    }
}

Set-DatasourceUid -Node $dashboard -Uid $promDs.uid

Write-Host "Ensuring DashNote folder exists ..."
$folderUid = "dashnote"
$folderPayload = @{ uid = $folderUid; title = "DashNote" } | ConvertTo-Json
try {
    Invoke-RestMethod -Uri "$stackUrl/api/folders" -Headers $headers -Method Post -Body $folderPayload | Out-Null
    Write-Host "Created folder: DashNote"
} catch {
    Write-Host "Folder DashNote already exists or could not be created (continuing)."
}

$importBody = @{
    dashboard = $dashboard
    folderUid = $folderUid
    overwrite = $true
    message   = "Import DashNote API Overview from repo"
} | ConvertTo-Json -Depth 30

Write-Host "Importing dashboard API Overview ..."
$result = Invoke-RestMethod -Uri "$stackUrl/api/dashboards/db" -Headers $headers -Method Post -Body $importBody
$url = "$stackUrl$($result.url)"
Write-Host ""
Write-Host "SUCCESS: Dashboard imported."
Write-Host "  Title: $($result.title)"
Write-Host "  UID:   $($result.uid)"
Write-Host "  URL:   $url"
Write-Host ""
Write-Host "Verify panels show data after generating traffic:"
Write-Host "  curl http://localhost:8000/health"
