#requires -Version 5.1

<#
.SYNOPSIS
Runs and validates concept extraction for a downloaded zh.ch fixture.

.DESCRIPTION
Passes the supplied directory to swisstip-concepts, which scans supported page
files recursively. The script validates structural POC invariants and writes the
JSON only after the command succeeds and the result passes validation.

Provider selection remains the active_profile value in semantic-models.toml.
For a Hugging Face profile, HF_TOKEN is read from the calling process first and
then from the repository-root .env.dev file. The value is passed only to the
child Python process and is never printed.

.PARAMETER PagesRoot
Directory containing the downloaded page hierarchy.

.PARAMETER ConfigPath
Semantic-model configuration file. Defaults to config/semantic-models.toml in
the repository.

.PARAMETER EnvFilePath
Optional dotenv file containing HF_TOKEN. Defaults to .env.dev in the
repository root. A token already set in the calling process takes precedence.

.PARAMETER ManifestPath
Download manifest created by Save-ZhChTestPages.ps1. Defaults to
download-manifest.json beside PagesRoot. It is verified before model calls.

.PARAMETER OutputPath
Destination JSON file. Defaults to concept-proposals.json beside PagesRoot.

.PARAMETER ExpectedPageCount
Expected number of reports. The fixed zh.ch fixture contains six pages.

.PARAMETER MaxFileBytes
Maximum input file size passed to swisstip-concepts. Keep this aligned with the
download limit used by Save-ZhChTestPages.ps1.

.PARAMETER Force
Allows replacement of an existing OutputPath after a successful extraction.

.EXAMPLE
./scripts/test/zhch/Test-ZhChConceptExtraction.ps1 `
    -PagesRoot C:\Temp\swisstip-zhch\pages
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $PagesRoot,

    [Parameter()]
    [string] $ConfigPath,

    [Parameter()]
    [string] $EnvFilePath,

    [Parameter()]
    [string] $ManifestPath,

    [Parameter()]
    [string] $OutputPath,

    [Parameter()]
    [ValidateRange(1, 1000)]
    [int] $ExpectedPageCount = 6,

    [Parameter()]
    [ValidateRange(1, 2147483647)]
    [long] $MaxFileBytes = 2000000,

    [Parameter()]
    [switch] $Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_NativeCli.ps1")

$repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\.."))
$conceptExecutable = Join-Path $repositoryRoot ".venv\Scripts\swisstip-concepts.exe"
$utf8NoBom = [Text.UTF8Encoding]::new($false)

if (-not (Test-Path -LiteralPath $conceptExecutable -PathType Leaf)) {
    throw "Concept extractor not found at $conceptExecutable. Install the workspace into .venv first."
}
if (-not (Test-Path -LiteralPath $PagesRoot -PathType Container)) {
    throw "PagesRoot is not an existing directory: $PagesRoot"
}

$resolvedPagesRoot = (Resolve-Path -LiteralPath $PagesRoot).Path
if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $ConfigPath = Join-Path $repositoryRoot "config\semantic-models.toml"
}
if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
    throw "ConfigPath is not an existing file: $ConfigPath"
}
$resolvedConfigPath = (Resolve-Path -LiteralPath $ConfigPath).Path

$envFileWasExplicit = -not [string]::IsNullOrWhiteSpace($EnvFilePath)
if (-not $envFileWasExplicit) {
    $EnvFilePath = Join-Path $repositoryRoot ".env.dev"
}
$resolvedEnvFilePath = $null
if (Test-Path -LiteralPath $EnvFilePath -PathType Leaf) {
    $resolvedEnvFilePath = (Resolve-Path -LiteralPath $EnvFilePath).Path
}
elseif ($envFileWasExplicit) {
    throw "EnvFilePath is not an existing file: $EnvFilePath"
}

$childEnvironmentVariables = @{}
$tokenSource = "none"
$processToken = [Environment]::GetEnvironmentVariable("HF_TOKEN", "Process")
if (-not [string]::IsNullOrWhiteSpace($processToken)) {
    $tokenSource = "process"
}
elseif ($null -ne $resolvedEnvFilePath) {
    $fileToken = Get-SwissTipEnvFileValue `
        -Path $resolvedEnvFilePath `
        -Name "HF_TOKEN"
    if (-not [string]::IsNullOrWhiteSpace($fileToken)) {
        $childEnvironmentVariables["HF_TOKEN"] = $fileToken
        $tokenSource = "env-file"
    }
}

if ([string]::IsNullOrWhiteSpace($ManifestPath)) {
    $ManifestPath = Join-Path (
        (Split-Path -Parent $resolvedPagesRoot)
    ) "download-manifest.json"
}
if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
    throw (
        "ManifestPath is not an existing file: $ManifestPath. " +
        "Create the fixture with Save-ZhChTestPages.ps1 first."
    )
}
$resolvedManifestPath = (Resolve-Path -LiteralPath $ManifestPath).Path

try {
    $manifest = Get-Content -LiteralPath $resolvedManifestPath -Raw |
        ConvertFrom-Json
}
catch {
    throw "Download manifest is invalid JSON: $($_.Exception.Message)"
}
if ($manifest.schema_version -ne "swisstip.zhch-test-fixture/v1") {
    throw "Unexpected download manifest schema: $($manifest.schema_version)"
}
if ([int] $manifest.page_count -ne $ExpectedPageCount) {
    throw (
        "Manifest declares $($manifest.page_count) pages instead of " +
        "$ExpectedPageCount."
    )
}

$manifestPages = @($manifest.pages)
if ($manifestPages.Count -ne $ExpectedPageCount) {
    throw (
        "Manifest page array contains $($manifestPages.Count) entries instead " +
        "of $ExpectedPageCount."
    )
}

$pagesRootPrefix = $resolvedPagesRoot.TrimEnd(
    [IO.Path]::DirectorySeparatorChar,
    [IO.Path]::AltDirectorySeparatorChar
) + [IO.Path]::DirectorySeparatorChar
$expectedSourcePaths = @()
foreach ($manifestPage in $manifestPages) {
    $relativePath = [string] $manifestPage.relative_path
    $pathSegments = @($relativePath -split "/")
    if (
        [string]::IsNullOrWhiteSpace($relativePath) -or
        @($pathSegments | Where-Object { $_ -in @("", ".", "..") }).Count -gt 0
    ) {
        throw "Manifest contains an unsafe relative path: $relativePath"
    }

    $nativeRelativePath = $pathSegments -join [IO.Path]::DirectorySeparatorChar
    $expectedPath = [IO.Path]::GetFullPath(
        (Join-Path $resolvedPagesRoot $nativeRelativePath)
    )
    if (-not $expectedPath.StartsWith(
        $pagesRootPrefix,
        [StringComparison]::OrdinalIgnoreCase
    )) {
        throw "Manifest page resolves outside PagesRoot: $relativePath"
    }
    if (-not (Test-Path -LiteralPath $expectedPath -PathType Leaf)) {
        throw "Manifest page is missing: $expectedPath"
    }

    $pageFile = Get-Item -LiteralPath $expectedPath
    if ($pageFile.Length -ne [long] $manifestPage.bytes) {
        throw "Manifest byte count differs from the saved page: $expectedPath"
    }
    if ($pageFile.Length -gt $MaxFileBytes) {
        throw "Manifest page exceeds MaxFileBytes: $expectedPath"
    }

    $actualHash = (
        Get-FileHash -LiteralPath $expectedPath -Algorithm SHA256
    ).Hash.ToLowerInvariant()
    $manifestHash = ([string] $manifestPage.sha256).ToLowerInvariant()
    if ([string]::IsNullOrWhiteSpace($manifestHash) -or $actualHash -ne $manifestHash) {
        throw "Manifest hash differs from the saved page: $expectedPath"
    }

    $expectedSourcePaths += $expectedPath
}

$uniqueExpectedSourcePaths = @(
    $expectedSourcePaths |
        ForEach-Object { $_.ToLowerInvariant() } |
        Sort-Object -Unique
)
if ($uniqueExpectedSourcePaths.Count -ne $ExpectedPageCount) {
    throw "Manifest contains duplicate page paths."
}
Write-Verbose (
    "Verified manifest and SHA256 hashes for {0} downloaded page(s): {1}" -f
    $ExpectedPageCount,
    $resolvedManifestPath
)

$supportedExtensions = @(".html", ".htm", ".txt", ".md", ".markdown")
$discoveredSourcePaths = @(
    Get-ChildItem -LiteralPath $resolvedPagesRoot -File -Recurse -Force |
        Where-Object {
            $_.Extension.ToLowerInvariant() -in $supportedExtensions -and
            -not ($_.Attributes -band [IO.FileAttributes]::ReparsePoint)
        } |
        ForEach-Object { $_.FullName.ToLowerInvariant() } |
        Sort-Object
)
$expectedSourcePathsBeforeModel = @(
    $expectedSourcePaths |
        ForEach-Object { $_.ToLowerInvariant() } |
        Sort-Object
)
if (
    [string]::Join("`n", $discoveredSourcePaths) -ne
    [string]::Join("`n", $expectedSourcePathsBeforeModel)
) {
    throw (
        "Supported files beneath PagesRoot do not match the manifest. " +
        "No model request was made."
    )
}
Write-Verbose (
    "Verified recursive input scan: {0} supported page(s), no unexpected inputs." -f
    $discoveredSourcePaths.Count
)

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path (
        (Split-Path -Parent $resolvedPagesRoot)
    ) "concept-proposals.json"
}
$resolvedOutputPath = [IO.Path]::GetFullPath($OutputPath)
if ([IO.Path]::GetExtension($resolvedOutputPath) -ne ".json") {
    throw "OutputPath must use the .json extension: $resolvedOutputPath"
}
if (
    $resolvedOutputPath.Equals(
        $resolvedManifestPath,
        [StringComparison]::OrdinalIgnoreCase
    ) -or
    $resolvedOutputPath.Equals(
        $resolvedConfigPath,
        [StringComparison]::OrdinalIgnoreCase
    )
) {
    throw "OutputPath must not replace the manifest or model configuration."
}
if (Test-Path -LiteralPath $resolvedOutputPath -PathType Container) {
    throw "OutputPath identifies a directory: $resolvedOutputPath"
}
if ((Test-Path -LiteralPath $resolvedOutputPath) -and -not $Force) {
    throw "OutputPath already exists. Select another path or pass -Force: $resolvedOutputPath"
}

$outputDirectory = Split-Path -Parent $resolvedOutputPath
if (-not (Test-Path -LiteralPath $outputDirectory)) {
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
}

$cliArguments = @(
    $resolvedPagesRoot
    "--config"
    $resolvedConfigPath
    "--max-file-bytes"
    "$MaxFileBytes"
    "--compact"
)
$streamProgress = $VerbosePreference -ne "SilentlyContinue"
if ($streamProgress) {
    $cliArguments += "--verbose"
}

Write-Verbose "Semantic-model configuration: $resolvedConfigPath"
Write-Verbose "HF_TOKEN source for the child process: $tokenSource"
Write-Verbose "Validated result destination: $resolvedOutputPath"
Write-Verbose "Running recursive concept extraction for $resolvedPagesRoot"
$conceptInvocation = Invoke-SwissTipNativeCommand `
    -FilePath $conceptExecutable `
    -Arguments $cliArguments `
    -WorkingDirectory $repositoryRoot `
    -EnvironmentVariables $childEnvironmentVariables `
    -StreamStandardErrorAsVerbose:$streamProgress
if ($conceptInvocation.ExitCode -ne 0) {
    $errorDetail = $conceptInvocation.StandardError.Trim()
    if ($streamProgress) {
        $errorLines = @(
            $errorDetail -split "`r?`n" |
                Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
        )
        if ($errorLines.Count -gt 0) {
            $errorDetail = $errorLines[-1]
        }
    }
    elseif ($errorDetail.Length -gt 4000) {
        $errorDetail = "..." + $errorDetail.Substring($errorDetail.Length - 4000)
    }
    throw (
        "Concept extraction failed with exit code $($conceptInvocation.ExitCode). " +
        "No result file was written. $errorDetail"
    )
}

Write-Verbose "Concept extractor returned successfully; validating JSON output."

$outputText = $conceptInvocation.StandardOutput
if ([string]::IsNullOrWhiteSpace($outputText)) {
    throw "Concept extraction returned no JSON."
}

try {
    $batch = $outputText | ConvertFrom-Json
}
catch {
    throw "Concept extraction returned invalid JSON: $($_.Exception.Message)"
}

if ($batch.schema_version -ne "swisstip.concept-proposal-batch/v1") {
    throw "Unexpected batch schema version: $($batch.schema_version)"
}
if ([int] $batch.report_count -ne $ExpectedPageCount) {
    throw "Expected $ExpectedPageCount reports, received $($batch.report_count)."
}

$reports = @($batch.reports)
if ($reports.Count -ne $ExpectedPageCount) {
    throw "Report array contains $($reports.Count) entries instead of $ExpectedPageCount."
}

$sources = @($reports | ForEach-Object { [string] $_.source })
$uniqueSources = @($sources | Sort-Object -Unique)
if ($uniqueSources.Count -ne $sources.Count) {
    throw "The extraction result contains duplicate report sources."
}
$actualSourcePaths = @(
    $sources |
        ForEach-Object { [IO.Path]::GetFullPath($_).ToLowerInvariant() } |
        Sort-Object
)
$expectedSourcePathsForComparison = @(
    $expectedSourcePaths |
        ForEach-Object { $_.ToLowerInvariant() } |
        Sort-Object
)
if (
    [string]::Join("`n", $actualSourcePaths) -ne
    [string]::Join("`n", $expectedSourcePathsForComparison)
) {
    throw "Extraction report sources do not match the download manifest."
}

$providers = @($reports | ForEach-Object { [string] $_.provider } | Sort-Object -Unique)
$models = @($reports | ForEach-Object { [string] $_.model } | Sort-Object -Unique)
if (
    $providers.Count -ne 1 -or
    [string]::IsNullOrWhiteSpace($providers[0]) -or
    $models.Count -ne 1 -or
    [string]::IsNullOrWhiteSpace($models[0])
) {
    throw "Extraction reports do not have one consistent provider and model."
}
if ([string]::IsNullOrWhiteSpace([string] $batch.active_profile)) {
    throw "Extraction batch has no active profile."
}

$candidateCount = 0
$warningCount = 0
$requestCount = 0
foreach ($report in $reports) {
    if ($report.schema_version -ne "swisstip.concept-proposal-report/v1") {
        throw "Unexpected report schema version: $($report.schema_version)"
    }
    if ([string]::IsNullOrWhiteSpace([string] $report.source)) {
        throw "A report has no source path."
    }
    if ([string]::IsNullOrWhiteSpace([string] $report.title)) {
        throw "Report has no title: $($report.source)"
    }
    if ([string]::IsNullOrWhiteSpace([string] $report.input_hash)) {
        throw "Report has no input hash: $($report.source)"
    }
    if ([string]::IsNullOrWhiteSpace([string] $report.output_hash)) {
        throw "Report has no output hash: $($report.source)"
    }
    if ($report.active_profile -ne $batch.active_profile) {
        throw "Report profile differs from batch profile: $($report.source)"
    }

    $requestCount += [int] $report.request_count
    $warningCount += @($report.warnings).Count
    $reportCandidates = @($report.candidates)
    if ($reportCandidates.Count -eq 0) {
        throw "Report contains no candidate concepts: $($report.source)"
    }
    foreach ($candidate in $reportCandidates) {
        $candidateCount++
        if ($candidate.validation_state -ne "CANDIDATE") {
            throw "Candidate has an unexpected validation state: $($candidate.candidate_id)"
        }
        if ([string]::IsNullOrWhiteSpace([string] $candidate.preferred_label)) {
            throw "Candidate has no preferred label: $($candidate.candidate_id)"
        }

        $evidenceItems = @($candidate.evidence)
        if ($evidenceItems.Count -eq 0) {
            throw "Candidate has no evidence: $($candidate.candidate_id)"
        }
        foreach ($evidence in $evidenceItems) {
            if (
                [string]::IsNullOrWhiteSpace([string] $evidence.section_id) -or
                [string]::IsNullOrWhiteSpace([string] $evidence.quote)
            ) {
                throw "Candidate contains incomplete evidence: $($candidate.candidate_id)"
            }
        }
    }
}

if ($candidateCount -eq 0) {
    throw "No candidate concepts were proposed."
}
Write-Verbose (
    "Validated extraction response: reports={0}, requests={1}, candidates={2}, warnings={3}." -f
    $reports.Count,
    $requestCount,
    $candidateCount,
    $warningCount
)

$partialOutputPath = "{0}.part-{1}" -f (
    $resolvedOutputPath,
    [Guid]::NewGuid().ToString("N")
)
try {
    [IO.File]::WriteAllText(
        $partialOutputPath,
        $outputText + [Environment]::NewLine,
        $utf8NoBom
    )
    if (Test-Path -LiteralPath $resolvedOutputPath) {
        Move-Item `
            -LiteralPath $partialOutputPath `
            -Destination $resolvedOutputPath `
            -Force
    }
    else {
        [IO.File]::Move($partialOutputPath, $resolvedOutputPath)
    }
}
finally {
    if (Test-Path -LiteralPath $partialOutputPath) {
        Remove-Item -LiteralPath $partialOutputPath -Force
    }
}
Write-Verbose "Saved validated concept proposals to $resolvedOutputPath"

if ($warningCount -gt 0) {
    Write-Warning (
        "Extraction produced $warningCount validation warning(s). " +
        "Review them in $resolvedOutputPath."
    )
}

return [pscustomobject] ([ordered] @{
    OutputPath = $resolvedOutputPath
    ManifestPath = $resolvedManifestPath
    TokenSource = $tokenSource
    ActiveProfile = [string] $batch.active_profile
    Provider = $providers[0]
    Model = $models[0]
    ReportCount = $reports.Count
    CandidateCount = $candidateCount
    WarningCount = $warningCount
    RequestCount = $requestCount
    ReviewTopics = @(
        "Permit types L, B, C, and G"
        "EU/EFTA and third-country admission"
        "Employment and non-employment residence"
        "Family reunification"
        "Biometric and lost permits"
        "Navigation, cookie, search, and contact noise rejection"
    )
})
