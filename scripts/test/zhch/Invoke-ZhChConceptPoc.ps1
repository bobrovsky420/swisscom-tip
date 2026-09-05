#requires -Version 5.1

<#
.SYNOPSIS
Downloads the fixed zh.ch fixture and runs the concept extraction POC.

.DESCRIPTION
Convenience wrapper for Save-ZhChTestPages.ps1 followed by
Test-ZhChConceptExtraction.ps1. The configured active_profile selects Ollama,
Hugging Face free, or Hugging Face paid. It uses HF_TOKEN from the calling
process when set, otherwise it reads HF_TOKEN from the repository-root
.env.dev file. The token is never printed.

A complete downloaded fixture is reused on later runs. The extraction script
revalidates its manifest, file sizes, and SHA-256 hashes before model calls.
Each extraction writes to a new runs/<RunName> folder, preserving older results.

.PARAMETER RunName
Optional unique label for this extraction, such as 8b-v2-01. Defaults to a
timestamp and random suffix. Existing run folders are never overwritten.

.PARAMETER OutputRoot
Directory for the fixture and results. The default is the stable
swisstip-zhch-poc directory beneath the system temp directory. An existing
complete fixture is reused; a new or empty directory is populated.

.PARAMETER RefreshFixture
Removes the selected OutputRoot, including runs and results, before downloading
a fresh fixture. Use a new OutputRoot to preserve comparison runs.

.PARAMETER FreshInference
Ignore existing model checkpoints for an independent model experiment. New
responses are still saved. Without this switch, matching responses are reused.

.PARAMETER ConfigPath
Semantic-model configuration file. The extraction script defaults this to the
repository config/semantic-models.toml file.

.PARAMETER EnvFilePath
Optional dotenv file containing HF_TOKEN. Defaults to .env.dev in the
repository root. A token already set in the calling process takes precedence.

.PARAMETER DelaySeconds
Minimum delay between network requests.

.PARAMETER MaxFileBytes
Maximum bytes accepted for one downloaded page.

.PARAMETER MaxTotalBytes
Maximum total bytes accepted for the six saved pages.

.PARAMETER RequestTimeoutSeconds
Timeout for individual network requests.

.EXAMPLE
# .env.dev contains: HF_TOKEN=hf_your_token_here
./scripts/test/zhch/Invoke-ZhChConceptPoc.ps1 -Verbose
#>

[CmdletBinding()]
param(
    [Parameter()]
    [string] $OutputRoot,

    [Parameter()]
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$')]
    [string] $RunName,

    [Parameter()]
    [switch] $FreshInference,

    [Parameter()]
    [string] $ConfigPath,

    [Parameter()]
    [string] $EnvFilePath,

    [Parameter()]
    [switch] $RefreshFixture,

    [Parameter()]
    [ValidateRange(0, 60)]
    [int] $DelaySeconds = 2,

    [Parameter()]
    [ValidateRange(1, 2147483647)]
    [long] $MaxFileBytes = 2000000,

    [Parameter()]
    [ValidateRange(1, 2147483647)]
    [long] $MaxTotalBytes = 12000000,

    [Parameter()]
    [ValidateRange(1, 600)]
    [int] $RequestTimeoutSeconds = 60
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\.."))
$downloadScript = Join-Path $PSScriptRoot "Save-ZhChTestPages.ps1"
$extractionScript = Join-Path $PSScriptRoot "Test-ZhChConceptExtraction.ps1"

function Get-ReusableFixture {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Root
    )

    if (-not (Test-Path -LiteralPath $Root)) {
        return $null
    }
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
        throw "OutputRoot is not a directory: $Root"
    }

    $existingEntries = @(Get-ChildItem -LiteralPath $Root -Force)
    if ($existingEntries.Count -eq 0) {
        return $null
    }

    $pagesRoot = Join-Path $Root "pages"
    $manifestPath = Join-Path $Root "download-manifest.json"
    $preflightPath = Join-Path $Root "crawl-preflight.json"
    if (
        -not (Test-Path -LiteralPath $pagesRoot -PathType Container) -or
        -not (Test-Path -LiteralPath $manifestPath -PathType Leaf) -or
        -not (Test-Path -LiteralPath $preflightPath -PathType Leaf)
    ) {
        throw (
            "OutputRoot contains an incomplete fixture: $Root. " +
            "Select another directory or pass -RefreshFixture."
        )
    }

    try {
        $manifest = Get-Content -LiteralPath $manifestPath -Raw |
            ConvertFrom-Json
    }
    catch {
        throw (
            "Cached download manifest is invalid JSON: $manifestPath. " +
            "Pass -RefreshFixture to download it again."
        )
    }
    $manifestPages = @($manifest.pages)
    if (
        $manifest.schema_version -ne "swisstip.zhch-test-fixture/v1" -or
        [int] $manifest.page_count -ne 6 -or
        $manifestPages.Count -ne 6
    ) {
        throw (
            "Cached download manifest is not the expected six-page fixture: " +
            "$manifestPath. Pass -RefreshFixture to download it again."
        )
    }

    return [pscustomobject] ([ordered] @{
        OutputRoot = $Root
        PagesRoot = $pagesRoot
        PageCount = 6
        TotalBytes = [long] $manifest.total_bytes
        PreflightPath = $preflightPath
        ManifestPath = $manifestPath
        Reused = $true
    })
}

if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $OutputRoot = Join-Path ([IO.Path]::GetTempPath()) "swisstip-zhch-poc"
}
$resolvedOutputRoot = [IO.Path]::GetFullPath($OutputRoot)
if ([string]::IsNullOrWhiteSpace($RunName)) {
    $RunName = (Get-Date -Format "yyyyMMdd-HHmmss-fff") + "-" + [Guid]::NewGuid().ToString("N").Substring(0, 8)
}
$runDirectory = Join-Path (Join-Path $resolvedOutputRoot "runs") $RunName
if ((Test-Path -LiteralPath $runDirectory) -and -not $RefreshFixture) {
    throw "Run already exists. Choose a new -RunName: $runDirectory"
}

if ($RefreshFixture -and (Test-Path -LiteralPath $resolvedOutputRoot)) {
    if (-not (Test-Path -LiteralPath $resolvedOutputRoot -PathType Container)) {
        throw "OutputRoot is not a directory: $resolvedOutputRoot"
    }
    $outputRootItem = Get-Item -LiteralPath $resolvedOutputRoot -Force
    if ($outputRootItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "Refusing to remove a linked OutputRoot: $resolvedOutputRoot"
    }
    $protectedRoots = @(
        [IO.Path]::GetPathRoot($resolvedOutputRoot)
        $repositoryRoot
        [Environment]::GetFolderPath([Environment+SpecialFolder]::UserProfile)
        [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    )
    foreach ($protectedRoot in $protectedRoots) {
        if (
            -not [string]::IsNullOrWhiteSpace($protectedRoot) -and
            $resolvedOutputRoot.Equals(
                [IO.Path]::GetFullPath($protectedRoot),
                [StringComparison]::OrdinalIgnoreCase
            )
        ) {
            throw "Refusing to remove protected OutputRoot: $resolvedOutputRoot"
        }
    }
    $cacheName = Split-Path -Leaf $resolvedOutputRoot
    $hasFixtureMarker = Test-Path -LiteralPath (
        (Join-Path $resolvedOutputRoot "download-manifest.json")
    ) -PathType Leaf
    $hasEntries = $null -ne (
        Get-ChildItem -LiteralPath $resolvedOutputRoot -Force |
            Select-Object -First 1
    )
    if (
        $hasEntries -and
        -not $hasFixtureMarker -and
        -not $cacheName.StartsWith(
            "swisstip-zhch",
            [StringComparison]::OrdinalIgnoreCase
        )
    ) {
        throw (
            "Refusing to refresh an unrecognized non-empty OutputRoot: " +
            "$resolvedOutputRoot"
        )
    }
    Write-Verbose "Removing cached fixture from $resolvedOutputRoot"
    Remove-Item -LiteralPath $resolvedOutputRoot -Recurse -Force
}

$fixture = Get-ReusableFixture -Root $resolvedOutputRoot
if ($null -ne $fixture) {
    Write-Verbose "Reusing downloaded fixture from $resolvedOutputRoot"
}

if ($null -eq $fixture) {
    $downloadParameters = @{
        OutputRoot = $resolvedOutputRoot
        DelaySeconds = $DelaySeconds
        MaxFileBytes = $MaxFileBytes
        MaxTotalBytes = $MaxTotalBytes
        RequestTimeoutSeconds = $RequestTimeoutSeconds
        Verbose = $VerbosePreference -ne "SilentlyContinue"
    }
    $fixture = & $downloadScript @downloadParameters
    $fixture | Add-Member -NotePropertyName Reused -NotePropertyValue $false
}

[void] (New-Item -ItemType Directory -Path $runDirectory)
$logPath = Join-Path $runDirectory "run.log"
$reviewPath = Join-Path $runDirectory "review.csv"
Copy-Item -LiteralPath $fixture.ManifestPath -Destination (Join-Path $runDirectory "download-manifest.json")

$extractionParameters = @{
    PagesRoot = $fixture.PagesRoot
    ManifestPath = $fixture.ManifestPath
    ExpectedPageCount = $fixture.PageCount
    MaxFileBytes = $MaxFileBytes
    OutputPath = Join-Path $runDirectory "concept-proposals.json"
    CheckpointDirectory = Join-Path $resolvedOutputRoot "checkpoints"
    FreshInference = $FreshInference
    # Capture progress in run.log even when the wrapper was invoked without -Verbose.
    Verbose = $true
}
if (-not [string]::IsNullOrWhiteSpace($ConfigPath)) {
    $extractionParameters.ConfigPath = $ConfigPath
}
if (-not [string]::IsNullOrWhiteSpace($EnvFilePath)) {
    $extractionParameters.EnvFilePath = $EnvFilePath
}

$transcriptStarted = $false
try {
    Start-Transcript -Path $logPath -NoClobber | Out-Null
    $transcriptStarted = $true
    $extraction = & $extractionScript @extractionParameters
    $batch = Get-Content -LiteralPath $extraction.OutputPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $reviewRows = @(
        foreach ($report in $batch.reports) {
            foreach ($candidate in $report.candidates) {
                [pscustomobject] ([ordered] @{
                    Source = $report.source
                    Title = $report.title
                    CandidateId = $candidate.candidate_id
                    Label = $candidate.preferred_label
                    Type = $candidate.concept_type
                    Granularity = $candidate.granularity
                    Scope = $candidate.scope
                    Description = $candidate.description
                    Questions = $candidate.user_questions -join " | "
                    Evidence = ($candidate.evidence | ForEach-Object { $_.quote }) -join " | "
                    PrimarySection = $candidate.primary_section_id
                    Relevant = ""
                    SupportedByEvidence = ""
                    CorrectType = ""
                    DuplicateOf = ""
                    Notes = ""
                })
            }
        }
    )
    if ($reviewRows.Count -gt 0) {
        $reviewRows | Export-Csv -LiteralPath $reviewPath -NoTypeInformation -Encoding UTF8
    }
    else {
        [IO.File]::WriteAllText(
            $reviewPath,
            "Source,Title,CandidateId,Label,Type,Granularity,Scope,Description,Questions,Evidence,PrimarySection,Relevant,SupportedByEvidence,CorrectType,DuplicateOf,Notes`r`n",
            [Text.UTF8Encoding]::new($false)
        )
    }
    Write-Verbose "Saved human review worksheet to $reviewPath"
}
catch {
    throw (
        "Concept extraction failed. The downloaded fixture remains at " +
        "$($fixture.OutputRoot) and will be reused on the next run. " +
        "Run diagnostics: $runDirectory. " +
        "$($_.Exception.Message)"
    )
}
finally {
    if ($transcriptStarted) {
        Stop-Transcript | Out-Null
    }
}

return [pscustomobject] ([ordered] @{
    OutputRoot = $fixture.OutputRoot
    PagesRoot = $fixture.PagesRoot
    ManifestPath = $fixture.ManifestPath
    PreflightPath = $fixture.PreflightPath
    FixtureReused = [bool] $fixture.Reused
    ProposalPath = $extraction.OutputPath
    RunDirectory = $runDirectory
    LogPath = $logPath
    ReviewPath = $reviewPath
    TokenSource = $extraction.TokenSource
    ActiveProfile = $extraction.ActiveProfile
    Provider = $extraction.Provider
    Model = $extraction.Model
    ReportCount = $extraction.ReportCount
    CandidateCount = $extraction.CandidateCount
    WarningCount = $extraction.WarningCount
    RequestCount = $extraction.RequestCount
    ReviewTopics = $extraction.ReviewTopics
})
