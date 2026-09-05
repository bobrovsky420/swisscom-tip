#requires -Version 5.1

function ConvertTo-SwissTipNativeArgument {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string] $Argument
    )

    if ($Argument.Length -gt 0 -and $Argument -notmatch '[\s"]') {
        return $Argument
    }

    $builder = [Text.StringBuilder]::new()
    $backslash = [string] [char] 92
    [void] $builder.Append([char] 34)
    $backslashCount = 0
    foreach ($character in $Argument.ToCharArray()) {
        if ($character -eq [char] 92) {
            $backslashCount++
            continue
        }

        if ($character -eq [char] 34) {
            if ($backslashCount -gt 0) {
                [void] $builder.Append(
                    $backslash * (($backslashCount * 2) + 1)
                )
            }
            else {
                [void] $builder.Append($backslash)
            }
            [void] $builder.Append([char] 34)
            $backslashCount = 0
            continue
        }

        if ($backslashCount -gt 0) {
            [void] $builder.Append($backslash * $backslashCount)
            $backslashCount = 0
        }
        [void] $builder.Append($character)
    }

    if ($backslashCount -gt 0) {
        [void] $builder.Append($backslash * ($backslashCount * 2))
    }
    [void] $builder.Append([char] 34)
    return $builder.ToString()
}

function Get-SwissTipEnvFileValue {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path,

        [Parameter(Mandatory = $true)]
        [ValidatePattern('^[A-Za-z_][A-Za-z0-9_]*$')]
        [string] $Name
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $null
    }

    $utf8Strict = [Text.UTF8Encoding]::new($false, $true)
    $found = $false
    $value = $null
    foreach ($line in [IO.File]::ReadAllLines($Path, $utf8Strict)) {
        $entry = $line.Trim()
        if ($entry.Length -eq 0 -or $entry.StartsWith("#")) {
            continue
        }
        if ($entry.StartsWith("export ", [StringComparison]::Ordinal)) {
            $entry = $entry.Substring(7).TrimStart()
        }

        $separatorIndex = $entry.IndexOf("=")
        if ($separatorIndex -lt 0) {
            if ($entry -match ("^" + [Regex]::Escape($Name) + "\b")) {
                throw "Malformed $Name entry in environment file: $Path"
            }
            continue
        }

        $entryName = $entry.Substring(0, $separatorIndex).Trim()
        if ($entryName -cne $Name) {
            continue
        }
        if ($found) {
            throw "Environment file contains more than one $Name entry: $Path"
        }

        $entryValue = $entry.Substring($separatorIndex + 1).Trim()
        if ($entryValue.Length -ge 2) {
            $firstCharacter = $entryValue[0]
            $lastCharacter = $entryValue[$entryValue.Length - 1]
            if (
                ($firstCharacter -eq [char] 34 -and $lastCharacter -eq [char] 34) -or
                ($firstCharacter -eq [char] 39 -and $lastCharacter -eq [char] 39)
            ) {
                $entryValue = $entryValue.Substring(1, $entryValue.Length - 2)
            }
            elseif (
                $firstCharacter -in @([char] 34, [char] 39) -or
                $lastCharacter -in @([char] 34, [char] 39)
            ) {
                throw "Malformed quoted $Name value in environment file: $Path"
            }
        }
        if ([string]::IsNullOrWhiteSpace($entryValue)) {
            throw "$Name is empty in environment file: $Path"
        }

        $found = $true
        $value = $entryValue
    }

    return $value
}

function Invoke-SwissTipNativeCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string] $FilePath,

        [Parameter()]
        [string[]] $Arguments = @(),

        [Parameter()]
        [string] $WorkingDirectory,

        [Parameter()]
        [hashtable] $EnvironmentVariables = @{},

        [Parameter()]
        [switch] $StreamStandardErrorAsVerbose
    )

    $encodedArguments = @(
        $Arguments |
            ForEach-Object { ConvertTo-SwissTipNativeArgument -Argument $_ }
    )
    $utf8Strict = [Text.UTF8Encoding]::new($false, $true)
    $startInfo = [Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $FilePath
    $startInfo.Arguments = $encodedArguments -join " "
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.WindowStyle = [Diagnostics.ProcessWindowStyle]::Hidden
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.StandardOutputEncoding = $utf8Strict
    $startInfo.StandardErrorEncoding = $utf8Strict
    foreach ($environmentName in $EnvironmentVariables.Keys) {
        if ([string] $environmentName -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
            throw "Invalid child-process environment variable name."
        }
        $startInfo.EnvironmentVariables[[string] $environmentName] = [string] (
            $EnvironmentVariables[$environmentName]
        )
    }
    $startInfo.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8"
    $startInfo.EnvironmentVariables["PYTHONUTF8"] = "1"
    if (-not [string]::IsNullOrWhiteSpace($WorkingDirectory)) {
        $startInfo.WorkingDirectory = $WorkingDirectory
    }

    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    try {
        if (-not $process.Start()) {
            throw "Native process did not start: $FilePath"
        }

        $standardOutputTask = $process.StandardOutput.ReadToEndAsync()
        if ($StreamStandardErrorAsVerbose) {
            $standardErrorBuilder = [Text.StringBuilder]::new()
            while ($null -ne ($standardErrorLine = $process.StandardError.ReadLine())) {
                [void] $standardErrorBuilder.AppendLine($standardErrorLine)
                Write-Verbose $standardErrorLine
            }
            $process.WaitForExit()
            $standardError = $standardErrorBuilder.ToString()
        }
        else {
            $standardErrorTask = $process.StandardError.ReadToEndAsync()
            $process.WaitForExit()
            $standardError = $standardErrorTask.GetAwaiter().GetResult()
        }
        $standardOutput = $standardOutputTask.GetAwaiter().GetResult()

        return [pscustomobject] ([ordered] @{
            ExitCode = $process.ExitCode
            StandardOutput = $standardOutput
            StandardError = $standardError
        })
    }
    finally {
        $process.Dispose()
    }
}
