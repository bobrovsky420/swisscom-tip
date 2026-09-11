param([Parameter(Mandatory=$true)][string]$Jobs)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[void][Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime]
[void][Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType=WindowsRuntime]
[void][Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
[void][Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
[void][Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]
[void][Windows.Media.Ocr.OcrResult, Windows.Foundation, ContentType=WindowsRuntime]
[void][Windows.Globalization.Language, Windows.Globalization, ContentType=WindowsRuntime]
$awaitMethod = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetGenericArguments().Count -eq 1 -and
    $_.GetParameters().Count -eq 1
} | Select-Object -First 1
function Wait-WinRt($Operation, [Type]$ResultType) {
    $task = $awaitMethod.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    $task.Wait()
    return $task.Result
}
$engines = @{}
$ocrJobs = Get-Content -LiteralPath $Jobs -Raw -Encoding UTF8 | ConvertFrom-Json
$processed = 0
foreach ($job in $ocrJobs) {
    if (Test-Path -LiteralPath $job.output) { continue }
    try {
        if (-not $engines.ContainsKey($job.recognizer_language)) {
            $language = [Windows.Globalization.Language]::new($job.recognizer_language)
            $engines[$job.recognizer_language] = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($language)
        }
        $file = Wait-WinRt ([Windows.Storage.StorageFile]::GetFileFromPathAsync($job.image)) ([Windows.Storage.StorageFile])
        $stream = Wait-WinRt ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
        try {
            $decoder = Wait-WinRt ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
            $bitmap = Wait-WinRt ($decoder.GetSoftwareBitmapAsync([Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8, [Windows.Graphics.Imaging.BitmapAlphaMode]::Premultiplied)) ([Windows.Graphics.Imaging.SoftwareBitmap])
            try {
                $result = Wait-WinRt ($engines[$job.recognizer_language].RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
                $lines = @($result.Lines | ForEach-Object {
                    @{text=$_.Text; words=@($_.Words | ForEach-Object {
                        @{text=$_.Text; x=$_.BoundingRect.X; y=$_.BoundingRect.Y; width=$_.BoundingRect.Width; height=$_.BoundingRect.Height}
                    })}
                })
                $record = @{status='ocr-completed'; text=$result.Text; lines=$lines; job=$job;
                    engine='Windows.Media.Ocr'; llm_calls=0; quality_reviewed=$false;
                    note='Machine-recognized text; retain image and verify before treating as an exact source quotation.'}
            } finally { $bitmap.Dispose() }
        } finally { $stream.Dispose() }
    } catch {
        $record = @{status='ocr-failed'; error=$_.Exception.Message; job=$job}
    }
    [System.IO.File]::WriteAllText($job.output, ($record | ConvertTo-Json -Depth 12), [System.Text.UTF8Encoding]::new($false))
    $processed++
    if ($processed % 20 -eq 0) { Write-Output "OCR processed: $processed" }
}
Write-Output "OCR finished; processed: $processed"
