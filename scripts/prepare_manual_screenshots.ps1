# Makes small copies of the manual screenshots for the app's Media.
#
# Usage (from the project folder):
#   powershell -ExecutionPolicy Bypass -File scripts/prepare_manual_screenshots.ps1 [folder]
#
# Reads files/manual-screenshots/S01.png, S02.jpg ... (named by the shot ID in
# "files/Manual - screenshot list.md") and writes files/manual-screenshots/app/help_s01.jpg ...
# at 450 px wide, JPEG quality 75 (about 40-80 KB each), so the app stays small.
# Then run: py -3 -I scripts/build_help_screen.py screens files
param([string]$Folder = "files/manual-screenshots")

Add-Type -AssemblyName System.Drawing
$out = Join-Path $Folder "app"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq "image/jpeg" }
$params = New-Object System.Drawing.Imaging.EncoderParameters 1
$params.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter ([System.Drawing.Imaging.Encoder]::Quality, [long]75)

$n = 0
Get-ChildItem -Path $Folder -File | Where-Object { $_.Name -match '^(S\d+)\.(png|jpe?g)$' } | ForEach-Object {
    $id = $Matches[1].ToLower()
    $src = [System.Drawing.Image]::FromFile($_.FullName)
    try {
        $w = [Math]::Min(450, $src.Width)
        $h = [int][Math]::Round($src.Height * $w / $src.Width)
        $bmp = New-Object System.Drawing.Bitmap $w, $h
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $g.DrawImage($src, 0, 0, $w, $h)
        $g.Dispose()
        $dest = Join-Path $out ("help_" + $id + ".jpg")
        $bmp.Save($dest, $codec, $params)
        $bmp.Dispose()
        $n++
        Write-Output ("{0} -> {1} ({2} KB)" -f $_.Name, $dest, [int]((Get-Item $dest).Length / 1KB))
    } finally {
        $src.Dispose()
    }
}
Write-Output "$n screenshot(s) prepared. Now run: py -3 -I scripts/build_help_screen.py screens files"
