#requires -Version 5.1

<#
.SYNOPSIS
Runs offline checks for the zh.ch PowerShell POC scripts.

.DESCRIPTION
Checks repository CLI availability, native argument quoting, lossless UTF-8
capture, and .env.dev parsing by running only local --help and --dry-run
commands. It makes no network or model requests.

.EXAMPLE
./scripts/test/zhch/Test-ZhChScriptEnvironment.ps1
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_NativeCli.ps1")

$repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\.."))
$crawlerPath = Join-Path $repositoryRoot ".venv\Scripts\swisstip-crawl.exe"
$conceptPath = Join-Path $repositoryRoot ".venv\Scripts\swisstip-concepts.exe"
$pythonPath = Join-Path $repositoryRoot ".venv\Scripts\python.exe"

foreach ($executable in @($crawlerPath, $conceptPath, $pythonPath)) {
    if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
        throw "Required executable not found: $executable"
    }
}

$authority = "Kanton Zürich"
$crawlerArguments = @(
    "https://www.zh.ch/de/migration-integration/aufenthalt.html"
    "--authority"
    $authority
    "--allow-path-prefix"
    "/de/migration-integration/aufenthalt.html"
    "--max-depth"
    "0"
    "--max-pages"
    "1"
    "--max-requests"
    "2"
    "--dry-run"
    "--compact"
)
$crawlerInvocation = Invoke-SwissTipNativeCommand `
    -FilePath $crawlerPath `
    -Arguments $crawlerArguments `
    -WorkingDirectory $repositoryRoot
if ($crawlerInvocation.ExitCode -ne 0) {
    throw "Crawler dry-run failed: $($crawlerInvocation.StandardError.Trim())"
}
$dryRun = $crawlerInvocation.StandardOutput | ConvertFrom-Json
if ($dryRun.mode -ne "dry-run") {
    throw "Crawler did not return a dry-run result."
}
if ($dryRun.source.canonical_authority -cne $authority) {
    throw "Native UTF-8 or argument round-trip failed."
}

$conceptInvocation = Invoke-SwissTipNativeCommand `
    -FilePath $conceptPath `
    -Arguments @("--help") `
    -WorkingDirectory $repositoryRoot
if ($conceptInvocation.ExitCode -ne 0) {
    throw "Concept CLI help failed: $($conceptInvocation.StandardError.Trim())"
}
if ($conceptInvocation.StandardOutput -notmatch "--max-file-bytes") {
    throw "Concept CLI help does not expose the expected input-size limit."
}
if ($conceptInvocation.StandardOutput -notmatch "--verbose") {
    throw "Concept CLI help does not expose live progress reporting."
}

$progressMarker = "swisstip-offline-progress-marker"
$progressInvocation = Invoke-SwissTipNativeCommand `
    -FilePath $pythonPath `
    -Arguments @(
        "-c"
        "import sys; print('swisstip-offline-progress-marker', file=sys.stderr, flush=True)"
    ) `
    -WorkingDirectory $repositoryRoot `
    -StreamStandardErrorAsVerbose
if ($progressInvocation.ExitCode -ne 0) {
    throw "Live progress capture check failed with a non-zero exit code."
}
if ($progressInvocation.StandardError.Trim() -cne $progressMarker) {
    throw "Live progress was not retained in captured standard error."
}
if (-not [string]::IsNullOrEmpty($progressInvocation.StandardOutput)) {
    throw "Live progress capture unexpectedly wrote to standard output."
}

$temporaryDirectory = Join-Path (
    [IO.Path]::GetTempPath()
) ("swisstip-env-test-" + [Guid]::NewGuid().ToString("N"))
$temporaryEnvFile = Join-Path $temporaryDirectory ".env.dev"
$expectedToken = "hf_offline_parser_test"
try {
    [void] [IO.Directory]::CreateDirectory($temporaryDirectory)
    [IO.File]::WriteAllText(
        $temporaryEnvFile,
        "# Offline parser fixture`r`nOTHER_VALUE=ignored`r`nHF_TOKEN=`"$expectedToken`"`r`n",
        [Text.UTF8Encoding]::new($false)
    )
    $parsedToken = Get-SwissTipEnvFileValue `
        -Path $temporaryEnvFile `
        -Name "HF_TOKEN"
    if ($parsedToken -cne $expectedToken) {
        throw ".env.dev token parsing failed."
    }

    $environmentInvocation = Invoke-SwissTipNativeCommand `
        -FilePath $pythonPath `
        -Arguments @(
            "-c"
            (
                "import os; raise SystemExit(0 if " +
                "os.environ.get('HF_TOKEN') == 'hf_offline_parser_test' else 1)"
            )
        ) `
        -WorkingDirectory $repositoryRoot `
        -EnvironmentVariables @{ HF_TOKEN = $parsedToken }
    if ($environmentInvocation.ExitCode -ne 0) {
        throw ".env.dev token was not passed to the child Python process."
    }
    if (
        -not [string]::IsNullOrEmpty($environmentInvocation.StandardOutput) -or
        -not [string]::IsNullOrEmpty($environmentInvocation.StandardError)
    ) {
        throw ".env.dev child-process check unexpectedly produced output."
    }
}
finally {
    if (Test-Path -LiteralPath $temporaryDirectory) {
        Remove-Item -LiteralPath $temporaryDirectory -Recurse -Force
    }
}

return [pscustomobject] ([ordered] @{
    PowerShellVersion = $PSVersionTable.PSVersion.ToString()
    CrawlerDryRun = "PASS"
    ConceptCli = "PASS"
    LiveProgressCapture = "PASS"
    Utf8RoundTrip = "PASS"
    EnvDevParsing = "PASS"
    NetworkRequests = 0
    ModelRequests = 0
})
