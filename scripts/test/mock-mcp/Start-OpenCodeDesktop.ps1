<#
.SYNOPSIS
Start the OpenCode desktop app with the mock or the real SwissTIP MCP configuration.

.DESCRIPTION
Uses the configuration files written by run_opencode_test.py under .local/mock-mcp/.
The configuration is passed through OPENCODE_CONFIG and, as an inline copy, through
OPENCODE_CONFIG_CONTENT. OpenCode applies the inline copy last, so it also overrides
a project-level opencode.json such as the one in the repository's .local folder.
The app is started with NUL standard handles and without the Electron and VS Code
variables that an editor-hosted shell carries, which would otherwise make the
Electron binary exit immediately. Nothing outside the app process is changed.

.EXAMPLE
./scripts/test/mock-mcp/Start-OpenCodeDesktop.ps1 -Server real
#>
param(
    [ValidateSet('mock', 'real')]
    [string]$Server = 'real'
)

$root = Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$fileName = if ($Server -eq 'mock') { 'opencode.json' } else { 'opencode-real.json' }
$config = Join-Path $root ".local\mock-mcp\$fileName"
if (-not (Test-Path $config)) {
    throw "Configuration not found: $config. Run run_opencode_test.py --server $Server --check-connection first."
}
$app = Join-Path $env:LOCALAPPDATA 'Programs\@opencode-aidesktop\OpenCode.exe'
if (-not (Test-Path $app)) {
    throw "OpenCode desktop app not found: $app"
}
$workspace = Join-Path $env:TEMP "swisstip-desktop-$Server"
New-Item -ItemType Directory -Force $workspace | Out-Null
Copy-Item $config (Join-Path $workspace 'opencode.json') -Force

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = Join-Path $env:SystemRoot 'System32\cmd.exe'
$psi.Arguments = "/c """"$app"" > NUL 2>&1 < NUL"""
$psi.WorkingDirectory = $workspace
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
foreach ($name in @($psi.Environment.Keys)) {
    if ($name -match '^(ELECTRON_|VSCODE_|CLAUDE|CHROME_CRASHPAD_PIPE_NAME|NODE_OPTIONS)') {
        $null = $psi.Environment.Remove($name)
    }
}
$psi.Environment['OPENCODE_CONFIG'] = $config
$psi.Environment['OPENCODE_CONFIG_CONTENT'] = Get-Content $config -Raw
$null = [System.Diagnostics.Process]::Start($psi)
Write-Host "OpenCode desktop started with the $Server configuration: $config"
Write-Host "Suggested project folder in the app: $workspace"
