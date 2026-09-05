#requires -Version 5.1

<#
.SYNOPSIS
Downloads the fixed zh.ch Aufenthalt test fixture.

.DESCRIPTION
Runs the repository crawler as a robots-aware preflight, verifies that all six
expected pages were audited, and then saves the exact HTML response bytes in a
nested directory tree. The script writes a SHA-256 manifest next to the pages.

The crawler preflight and saved downloads are separate requests. Their hashes
are recorded and compared so any content change between the requests is visible.

.PARAMETER OutputRoot
Directory that will contain pages, crawl-preflight.json, and download-manifest.json.
The default is a new uniquely named directory beneath the system temp directory.
An explicitly selected directory must be absent or empty.

.PARAMETER DelaySeconds
Minimum delay between requests. The crawler may impose a larger robots.txt delay.

.PARAMETER MaxFileBytes
Maximum number of bytes accepted for one downloaded HTML page.

.PARAMETER MaxTotalBytes
Maximum total number of bytes accepted for the six saved HTML pages.

.PARAMETER RequestTimeoutSeconds
Timeout for each direct HTML download.

.EXAMPLE
./scripts/test/zhch/Save-ZhChTestPages.ps1

.EXAMPLE
./scripts/test/zhch/Save-ZhChTestPages.ps1 -OutputRoot C:\Temp\swisstip-zhch
#>

[CmdletBinding()]
param(
    [Parameter()]
    [string] $OutputRoot,

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
Add-Type -AssemblyName System.Net.Http
. (Join-Path $PSScriptRoot "_NativeCli.ps1")

$repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\.."))
$crawlerPath = Join-Path $repositoryRoot ".venv\Scripts\swisstip-crawl.exe"
$utf8NoBom = [Text.UTF8Encoding]::new($false)
$userAgent = "SwissTIP-POC/0.1"
$runStartedAt = (Get-Date).ToUniversalTime().ToString("o")

$fixturePages = @(
    [pscustomobject]@{
        Url = "https://www.zh.ch/de/migration-integration/aufenthalt.html"
        RelativePath = "de/migration-integration/aufenthalt.html"
    }
    [pscustomobject]@{
        Url = "https://www.zh.ch/de/migration-integration/aufenthalt/aufenthalt-mit-erwerbstaetigkeit-fuer-drittstaatsangehoerige.html"
        RelativePath = "de/migration-integration/aufenthalt/aufenthalt-mit-erwerbstaetigkeit-fuer-drittstaatsangehoerige.html"
    }
    [pscustomobject]@{
        Url = "https://www.zh.ch/de/migration-integration/aufenthalt/aufenthalt-ohne-erwerbstaetigkeit-fuer-drittstaatsangehoerige.html"
        RelativePath = "de/migration-integration/aufenthalt/aufenthalt-ohne-erwerbstaetigkeit-fuer-drittstaatsangehoerige.html"
    }
    [pscustomobject]@{
        Url = "https://www.zh.ch/de/migration-integration/aufenthalt/aufenthalt-fuer-euefta-staatsangehoerige.html"
        RelativePath = "de/migration-integration/aufenthalt/aufenthalt-fuer-euefta-staatsangehoerige.html"
    }
    [pscustomobject]@{
        Url = "https://www.zh.ch/de/migration-integration/aufenthalt/familiennachzug-von-drittstaatsangehoerigen.html"
        RelativePath = "de/migration-integration/aufenthalt/familiennachzug-von-drittstaatsangehoerigen.html"
    }
    [pscustomobject]@{
        Url = "https://www.zh.ch/de/migration-integration/aufenthalt/biometrische-auslaenderausweise.html"
        RelativePath = "de/migration-integration/aufenthalt/biometrische-auslaenderausweise.html"
    }
)

function Write-AtomicUtf8File {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path,

        [Parameter(Mandatory = $true)]
        [string] $Content
    )

    $partialPath = "${Path}.part"
    if ((Test-Path -LiteralPath $Path) -or (Test-Path -LiteralPath $partialPath)) {
        throw "Refusing to overwrite an existing output file: $Path"
    }

    try {
        [IO.File]::WriteAllText($partialPath, $Content, $utf8NoBom)
        [IO.File]::Move($partialPath, $Path)
    }
    finally {
        if (Test-Path -LiteralPath $partialPath) {
            Remove-Item -LiteralPath $partialPath -Force
        }
    }
}

function Start-PoliteDelay {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateRange(0, [double]::MaxValue)]
        [double] $Seconds
    )

    if ($Seconds -eq 0) {
        return
    }

    $milliseconds = [Math]::Ceiling($Seconds * 1000)
    if ($milliseconds -gt [int]::MaxValue) {
        throw "The required robots delay is too large to schedule safely."
    }
    Start-Sleep -Milliseconds ([int] $milliseconds)
}

function Save-BoundedHttpsResponse {
    param(
        [Parameter(Mandatory = $true)]
        [Uri] $Uri,

        [Parameter(Mandatory = $true)]
        [string] $Path,

        [Parameter(Mandatory = $true)]
        [ValidateRange(1, 2147483647)]
        [long] $MaxBytes,

        [Parameter(Mandatory = $true)]
        [Net.Http.HttpClient] $HttpClient,

        [Parameter(Mandatory = $true)]
        [ValidateRange(1, 600)]
        [int] $TimeoutSeconds
    )

    $request = $null
    $response = $null
    $inputStream = $null
    $outputStream = $null
    $cancellation = $null
    try {
        $request = [Net.Http.HttpRequestMessage]::new(
            [Net.Http.HttpMethod]::Get,
            $Uri
        )
        $request.Headers.UserAgent.ParseAdd($userAgent)
        $request.Headers.Accept.ParseAdd("text/html")
        $request.Headers.Accept.ParseAdd("application/xhtml+xml")
        $request.Headers.AcceptEncoding.ParseAdd("identity")

        $cancellation = [Threading.CancellationTokenSource]::new()
        $cancellation.CancelAfter([TimeSpan]::FromSeconds($TimeoutSeconds))
        $sendTask = $HttpClient.SendAsync(
            $request,
            [Net.Http.HttpCompletionOption]::ResponseHeadersRead,
            $cancellation.Token
        )
        $response = $sendTask.GetAwaiter().GetResult()

        if ([int] $response.StatusCode -ne 200) {
            throw "Unexpected HTTP status for ${Uri}: $([int] $response.StatusCode)"
        }

        $contentTypeHeader = $response.Content.Headers.ContentType
        $mediaType = ""
        if ($null -ne $contentTypeHeader) {
            $mediaType = [string] $contentTypeHeader.MediaType
        }
        if ($mediaType -notin @("text/html", "application/xhtml+xml")) {
            throw "Unexpected content type for ${Uri}: $mediaType"
        }
        $unsupportedEncodings = @(
            $response.Content.Headers.ContentEncoding |
                Where-Object { $_ -ne "identity" }
        )
        if ($unsupportedEncodings.Count -gt 0) {
            throw "Unexpected content encoding for ${Uri}: $($unsupportedEncodings -join ',')"
        }

        $declaredLength = $response.Content.Headers.ContentLength
        if ($null -ne $declaredLength -and [long] $declaredLength -gt $MaxBytes) {
            throw "Declared response size exceeds the remaining byte limit: $Uri"
        }

        $inputStream = $response.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
        $outputStream = [IO.File]::Open(
            $Path,
            [IO.FileMode]::CreateNew,
            [IO.FileAccess]::Write,
            [IO.FileShare]::None
        )
        $buffer = [byte[]]::new(65536)
        $bytesReceived = 0L
        while ($true) {
            $remainingWithSentinel = ($MaxBytes - $bytesReceived) + 1L
            $readSize = [int] [Math]::Min(
                [long] $buffer.Length,
                $remainingWithSentinel
            )
            $readTask = $inputStream.ReadAsync(
                $buffer,
                0,
                $readSize,
                $cancellation.Token
            )
            $readCount = $readTask.GetAwaiter().GetResult()
            if ($readCount -eq 0) {
                break
            }

            $bytesReceived += $readCount
            if ($bytesReceived -gt $MaxBytes) {
                throw "Response exceeds the remaining byte limit: $Uri"
            }
            $outputStream.Write($buffer, 0, $readCount)
        }
        $outputStream.Flush($true)

        return [pscustomobject] ([ordered] @{
            Bytes = $bytesReceived
            ContentType = [string] $contentTypeHeader
            ETag = [string] $response.Headers.ETag
            LastModified = [string] $response.Content.Headers.LastModified
        })
    }
    finally {
        if ($null -ne $outputStream) {
            $outputStream.Dispose()
        }
        if ($null -ne $inputStream) {
            $inputStream.Dispose()
        }
        if ($null -ne $response) {
            $response.Dispose()
        }
        if ($null -ne $request) {
            $request.Dispose()
        }
        if ($null -ne $cancellation) {
            $cancellation.Dispose()
        }
    }
}

if (-not (Test-Path -LiteralPath $crawlerPath -PathType Leaf)) {
    throw "Crawler executable not found at $crawlerPath. Install the workspace into .venv first."
}

if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $directoryName = "swisstip-zhch-{0}" -f [Guid]::NewGuid().ToString("N")
    $OutputRoot = Join-Path ([IO.Path]::GetTempPath()) $directoryName
}

$resolvedOutputRoot = [IO.Path]::GetFullPath($OutputRoot)
if (Test-Path -LiteralPath $resolvedOutputRoot) {
    if (-not (Test-Path -LiteralPath $resolvedOutputRoot -PathType Container)) {
        throw "OutputRoot is not a directory: $resolvedOutputRoot"
    }

    $existingEntry = Get-ChildItem -LiteralPath $resolvedOutputRoot -Force |
        Select-Object -First 1
    if ($null -ne $existingEntry) {
        throw "OutputRoot must be empty: $resolvedOutputRoot"
    }
}
else {
    New-Item -ItemType Directory -Path $resolvedOutputRoot | Out-Null
}

$pagesRoot = Join-Path $resolvedOutputRoot "pages"
New-Item -ItemType Directory -Path $pagesRoot | Out-Null

foreach ($page in $fixturePages) {
    $uri = [Uri] $page.Url
    if (
        $uri.Scheme -ne "https" -or
        $uri.Host -ne "www.zh.ch" -or
        -not $uri.IsDefaultPort -or
        -not [string]::IsNullOrEmpty($uri.Query) -or
        -not [string]::IsNullOrEmpty($uri.Fragment)
    ) {
        throw "Fixture contains an unsafe URL: $($page.Url)"
    }
}

$crawlerByteLimit = $MaxTotalBytes + [Math]::Min(512000L, $MaxFileBytes)
$crawlerDurationSeconds = [Math]::Max(
    120,
    (($fixturePages.Count + 2) * $RequestTimeoutSeconds) +
        (($fixturePages.Count + 1) * $DelaySeconds)
)
$seedUrl = $fixturePages[0].Url
$crawlerArguments = @(
    $seedUrl
    "--source-id"
    "zhch-aufenthalt-de"
    "--authority"
    "Kanton Zurich"
    "--jurisdiction"
    "CH-ZH"
    "--language"
    "de"
    "--allow-path-prefix"
    "/de/migration-integration/aufenthalt.html"
    "--allow-path-prefix"
    "/de/migration-integration/aufenthalt/"
    "--max-depth"
    "1"
    "--max-pages"
    "$($fixturePages.Count)"
    "--max-requests"
    "8"
    "--max-total-bytes"
    "$crawlerByteLimit"
    "--max-response-bytes"
    "$MaxFileBytes"
    "--max-duration"
    "$crawlerDurationSeconds"
    "--timeout"
    "$RequestTimeoutSeconds"
    "--delay"
    "$DelaySeconds"
    "--max-redirects"
    "1"
    "--max-links-per-page"
    "2000"
    "--max-queued-urls"
    "100"
    "--max-failures"
    "1"
    "--user-agent"
    $userAgent
    "--compact"
)

Write-Verbose "Running robots-aware crawler preflight for the six fixed pages."
$preflightInvocation = Invoke-SwissTipNativeCommand `
    -FilePath $crawlerPath `
    -Arguments $crawlerArguments `
    -WorkingDirectory $repositoryRoot
if ($preflightInvocation.ExitCode -ne 0) {
    $errorDetail = $preflightInvocation.StandardError.Trim()
    if ($errorDetail.Length -gt 2000) {
        $errorDetail = $errorDetail.Substring(0, 2000)
    }
    throw (
        "Crawler preflight failed with exit code " +
        "$($preflightInvocation.ExitCode). $errorDetail"
    )
}

$preflightText = $preflightInvocation.StandardOutput
if ([string]::IsNullOrWhiteSpace($preflightText)) {
    throw "Crawler preflight returned no JSON."
}

try {
    $preflightEnvelope = $preflightText | ConvertFrom-Json
}
catch {
    throw "Crawler preflight returned invalid JSON: $($_.Exception.Message)"
}

if ($preflightEnvelope.mode -ne "crawl" -or $null -eq $preflightEnvelope.report) {
    throw "Crawler preflight returned an unexpected result envelope."
}
$preflightReport = $preflightEnvelope.report

if ($preflightReport.robots_status -notin @("loaded", "not-published")) {
    throw "Crawler preflight did not obtain a usable robots policy: $($preflightReport.robots_status)"
}
if ([int] $preflightReport.failures -ne 0) {
    throw "Crawler preflight reported $($preflightReport.failures) failure(s)."
}

$preflightByUrl = @{}
foreach ($expectedPage in $fixturePages) {
    $matchingPages = @(
        $preflightReport.pages |
            Where-Object { $_.requested_url -eq $expectedPage.Url }
    )
    if ($matchingPages.Count -ne 1) {
        throw (
            "Crawler preflight did not audit exactly once: $($expectedPage.Url). " +
            "The robots policy or landing-page section links may have changed."
        )
    }

    $auditedPage = $matchingPages[0]
    if (
        $auditedPage.final_url -ne $expectedPage.Url -or
        [int] $auditedPage.status -ne 200 -or
        $auditedPage.outcome -ne "fetched" -or
        $auditedPage.content_type -notin @("text/html", "application/xhtml+xml") -or
        [string]::IsNullOrWhiteSpace([string] $auditedPage.sha256)
    ) {
        throw "Crawler preflight rejected or could not verify: $($expectedPage.Url)"
    }

    $preflightByUrl[$expectedPage.Url] = $auditedPage
}

$preflightPath = Join-Path $resolvedOutputRoot "crawl-preflight.json"
Write-AtomicUtf8File `
    -Path $preflightPath `
    -Content ($preflightText + [Environment]::NewLine)

$directDelaySeconds = [Math]::Max(
    [double] $DelaySeconds,
    [double] $preflightReport.effective_delay_seconds
)
Write-Verbose "Waiting $directDelaySeconds second(s) after crawler preflight."
Start-PoliteDelay -Seconds $directDelaySeconds

$manifestEntries = @()
$totalBytes = 0L
$httpHandler = [Net.Http.HttpClientHandler]::new()
$httpHandler.AllowAutoRedirect = $false
$httpHandler.UseCookies = $false
$httpHandler.AutomaticDecompression = [Net.DecompressionMethods]::None
$httpClient = [Net.Http.HttpClient]::new($httpHandler)
$httpClient.Timeout = [Threading.Timeout]::InfiniteTimeSpan
try {
    for ($index = 0; $index -lt $fixturePages.Count; $index++) {
        $page = $fixturePages[$index]
        $relativeNativePath = ($page.RelativePath -split "/") -join (
            [IO.Path]::DirectorySeparatorChar
        )
        $targetPath = Join-Path $pagesRoot $relativeNativePath
        $targetDirectory = Split-Path -Parent $targetPath
        $partialPath = "${targetPath}.part"

        New-Item -ItemType Directory -Path $targetDirectory -Force | Out-Null
        if ((Test-Path -LiteralPath $targetPath) -or (Test-Path -LiteralPath $partialPath)) {
            throw "Refusing to overwrite an existing page file: $targetPath"
        }

        $remainingTotalBytes = $MaxTotalBytes - $totalBytes
        $responseByteLimit = [Math]::Min($MaxFileBytes, $remainingTotalBytes)
        if ($responseByteLimit -lt 1) {
            throw "Downloaded pages reached MaxTotalBytes."
        }

        Write-Verbose "Downloading $($page.Url)"
        try {
            $download = Save-BoundedHttpsResponse `
                -Uri ([Uri] $page.Url) `
                -Path $partialPath `
                -MaxBytes $responseByteLimit `
                -HttpClient $httpClient `
                -TimeoutSeconds $RequestTimeoutSeconds

            $downloadHash = (
                Get-FileHash -LiteralPath $partialPath -Algorithm SHA256
            ).Hash.ToLowerInvariant()
            $preflightHash = (
                [string] $preflightByUrl[$page.Url].sha256
            ).ToLowerInvariant()
            $matchesPreflight = $downloadHash -eq $preflightHash
            if (-not $matchesPreflight) {
                Write-Warning "Page changed between crawler preflight and saved download: $($page.Url)"
            }

            [IO.File]::Move($partialPath, $targetPath)
            $totalBytes += $download.Bytes
            $manifestEntries += [pscustomobject] ([ordered] @{
                url = $page.Url
                relative_path = $page.RelativePath
                bytes = $download.Bytes
                sha256 = $downloadHash
                preflight_sha256 = $preflightHash
                matches_preflight = $matchesPreflight
                retrieved_at = (Get-Date).ToUniversalTime().ToString("o")
                content_type = $download.ContentType
                etag = $download.ETag
                last_modified = $download.LastModified
            })
        }
        finally {
            if (Test-Path -LiteralPath $partialPath) {
                Remove-Item -LiteralPath $partialPath -Force
            }
        }

        if ($index -lt ($fixturePages.Count - 1) -and $directDelaySeconds -gt 0) {
            Start-PoliteDelay -Seconds $directDelaySeconds
        }
    }
}
catch {
    throw (
        "Fixture download failed. Partial output remains at " +
        "$resolvedOutputRoot. $($_.Exception.Message)"
    )
}
finally {
    $httpClient.Dispose()
}

$manifest = [ordered] @{
    schema_version = "swisstip.zhch-test-fixture/v1"
    source_section = $seedUrl
    robots_url = "https://www.zh.ch/robots.txt"
    usage_terms_url = "https://www.zh.ch/de/nutzungshinweise.html"
    run_started_at = $runStartedAt
    run_finished_at = (Get-Date).ToUniversalTime().ToString("o")
    page_count = $manifestEntries.Count
    total_bytes = $totalBytes
    pages = $manifestEntries
}
$manifestText = $manifest | ConvertTo-Json -Depth 6
$manifestPath = Join-Path $resolvedOutputRoot "download-manifest.json"
Write-AtomicUtf8File `
    -Path $manifestPath `
    -Content ($manifestText + [Environment]::NewLine)

Write-Warning (
    "Keep the fixture internal unless reuse is permitted by the zh.ch usage terms: " +
    "https://www.zh.ch/de/nutzungshinweise.html"
)

return [pscustomobject] ([ordered] @{
    OutputRoot = $resolvedOutputRoot
    PagesRoot = $pagesRoot
    PageCount = $manifestEntries.Count
    TotalBytes = $totalBytes
    PreflightPath = $preflightPath
    ManifestPath = $manifestPath
})
