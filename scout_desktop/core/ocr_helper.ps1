param(
    [string]$ImagePath = "",
    [switch]$Daemon = $false
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime

    $asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
    }

    function Await-Async($asyncOp, $targetType) {
        $method = $asTaskGeneric.MakeGenericMethod($targetType)
        $netTask = $method.Invoke($null, @($asyncOp))
        $netTask.Wait()
        return $netTask.Result
    }

    [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
    [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime] | Out-Null
    [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null

    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    if (-not $engine) {
        $lang = [Windows.Globalization.Language]::new("en-US")
        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
    }

    function Process-OcrImage([string]$targetPath) {
        try {
            if (-not (Test-Path $targetPath)) {
                $errObj = @{ "lines" = @(); "full_text" = ""; "error" = "FILE_NOT_FOUND" }
                [Console]::Out.WriteLine(($errObj | ConvertTo-Json -Compress))
                [Console]::Out.Flush()
                return
            }

            $resolved = (Resolve-Path $targetPath).Path
            $file = Await-Async ([Windows.Storage.StorageFile]::GetFileFromPathAsync($resolved)) ([Windows.Storage.StorageFile])
            $stream = Await-Async ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
            $decoder = Await-Async ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
            $bitmap = Await-Async ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
            $ocrResult = Await-Async ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])

            $lines = @()
            foreach ($line in $ocrResult.Lines) {
                $cleanLine = $line.Text -replace '[\u0000-\u0008\u000B\u000C\u000E-\u001F]', ' '
                $cleanLine = $cleanLine.Trim()
                if ($cleanLine.Length -gt 0) {
                    $lines += $cleanLine
                }
            }

            $cleanFull = $ocrResult.Text -replace '[\u0000-\u0008\u000B\u000C\u000E-\u001F]', ' '
            $outObj = @{
                "lines" = $lines
                "full_text" = $cleanFull.Trim()
            }

            [Console]::Out.WriteLine(($outObj | ConvertTo-Json -Compress))
            [Console]::Out.Flush()
        } catch {
            $errObj = @{ "lines" = @(); "full_text" = ""; "error" = $_.Exception.Message }
            [Console]::Out.WriteLine(($errObj | ConvertTo-Json -Compress))
            [Console]::Out.Flush()
        }
    }

    if ($Daemon) {
        [Console]::Out.WriteLine("DAEMON_READY")
        [Console]::Out.Flush()

        while ($true) {
            $inputLine = [Console]::In.ReadLine()
            if ($null -eq $inputLine -or $inputLine -eq "QUIT" -or $inputLine -eq "EXIT") {
                break
            }
            $target = $inputLine.Trim()
            if ($target.Length -gt 0) {
                Process-OcrImage $target
            }
        }
    } else {
        if ($ImagePath) {
            Process-OcrImage $ImagePath
        }
    }

} catch {
    [Console]::Out.WriteLine("ERROR: $($_.Exception.Message)")
    [Console]::Out.Flush()
}
