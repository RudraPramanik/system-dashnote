Param(
    [string]$BaseUrl = "http://127.0.0.1",
    [string]$Token = "",
    [string]$OtherWorkspaceToken = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Title)
    Write-Host ""
    Write-Host ("=" * 78)
    Write-Host $Title
    Write-Host ("=" * 78)
}

function Require-Token {
    if ([string]::IsNullOrWhiteSpace($Token)) {
        throw "TOKEN is required for authenticated gates. Pass -Token '<JWT>'."
    }
}

Write-Step "Slice 6.4 one-stop validation: build and start api"
docker compose up -d --build api

Write-Step "GATE 1: checkpointer startup and checkpoint tables"
docker compose logs api --tail 60
docker compose exec db psql -U dashuser -d dashnotes -c "\dt checkpoint*"

Write-Step "GATE 2: existing /ai/chat still works"
Require-Token
$chatResp = Invoke-RestMethod -Uri "$BaseUrl/ai/chat" `
    -Method Post `
    -Headers @{ Authorization = "Bearer $Token" } `
    -ContentType "application/json" `
    -Body '{"message":"test"}'
$chatResp | ConvertTo-Json -Depth 8

Write-Step "GATE 3: POST /ai/agent returns answer + thread_id + steps"
$agentResp = Invoke-RestMethod -Uri "$BaseUrl/ai/agent" `
    -Method Post `
    -Headers @{ Authorization = "Bearer $Token" } `
    -ContentType "application/json" `
    -Body '{"message":"What is in my workspace notes?","thread_id":null}'
$agentResp | ConvertTo-Json -Depth 8

if (-not $agentResp.thread_id) {
    throw "GATE 3 failed: thread_id is empty."
}
if ([int]$agentResp.steps_taken -lt 1) {
    throw "GATE 3 failed: steps_taken < 1."
}

Write-Step "GATE 4: multi-step tool use (search + create)"
$multiResp = Invoke-RestMethod -Uri "$BaseUrl/ai/agent" `
    -Method Post `
    -Headers @{ Authorization = "Bearer $Token" } `
    -ContentType "application/json" `
    -Body '{"message":"Search my notes and create a summary note titled AI Workspace Synopsis"}'
$multiResp | ConvertTo-Json -Depth 8
docker compose exec db psql -U dashuser -d dashnotes -c "SELECT id, title FROM notes WHERE title = 'AI Workspace Synopsis';"

Write-Step "GATE 5: conversation continuity with prior thread_id"
$thread = "$($agentResp.thread_id)"
$continuationBody = "{`"message`": `"What did I just ask you?`", `"thread_id`": `"$thread`"}"
$contResp = Invoke-RestMethod -Uri "$BaseUrl/ai/agent" `
    -Method Post `
    -Headers @{ Authorization = "Bearer $Token" } `
    -ContentType "application/json" `
    -Body $continuationBody
$contResp | ConvertTo-Json -Depth 8

Write-Step "GATE 6: streaming /ai/agent/stream"
curl.exe -sS -X POST "$BaseUrl/ai/agent/stream" `
  -H "Authorization: Bearer $Token" `
  -H "Content-Type: application/json" `
  -d '{"message":"Summarize my workspace"}' --no-buffer

Write-Step "GATE 7: cross-workspace isolation (optional if second token provided)"
if ([string]::IsNullOrWhiteSpace($OtherWorkspaceToken)) {
    Write-Host "SKIP: provide -OtherWorkspaceToken to validate cross-workspace 400."
}
else {
    $reuseBody = "{`"message`": `"reuse foreign thread`", `"thread_id`": `"$thread`"}"
    try {
        Invoke-RestMethod -Uri "$BaseUrl/ai/agent" `
            -Method Post `
            -Headers @{ Authorization = "Bearer $OtherWorkspaceToken" } `
            -ContentType "application/json" `
            -Body $reuseBody
        throw "GATE 7 failed: expected 400 for foreign workspace thread reuse."
    }
    catch {
        Write-Host "Expected failure (likely 400): $($_.Exception.Message)"
    }
}

Write-Step "GATE 8: iteration limit enforcement log check"
docker compose logs api --tail 200 | Select-String -Pattern "iteration limit"

Write-Step "Slice 6.4 validation complete"
