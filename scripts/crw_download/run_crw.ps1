[CmdletBinding()]
param(
    [switch]$Regional,
    [switch]$Sample,
    [switch]$VerifyOnly,
    [switch]$Full,
    [string]$DataDirectory,
    [string]$PythonExecutable = 'python'
)
$ErrorActionPreference = 'Stop'
if ($Regional -and $Full) { throw 'Choose -Regional or -Full.' }
if (($Sample -or $VerifyOnly) -and -not $Regional) { throw 'Sample/VerifyOnly require -Regional.' }
$taskArguments = @((Join-Path $PSScriptRoot 'crw_downloader.py'))
if ($Regional) {
    $taskArguments += '--regional'
    if ($Sample) { $taskArguments += '--sample' }
    if ($VerifyOnly) { $taskArguments += '--verify-only' }
    if (-not $DataDirectory) {
        $DataDirectory = Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) 'Data\crw_regional'
        if ($Sample) { $DataDirectory = Join-Path $DataDirectory 'test' }
    }
} else {
    if ($Full) { $taskArguments += '--full' }
    if (-not $DataDirectory) { $DataDirectory = Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) 'Data\dhw_5km' }
}
$taskArguments += @('--output',$DataDirectory,'--timeout','300')
& $PythonExecutable @taskArguments
exit $LASTEXITCODE
