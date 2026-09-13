param([switch]$CheckOnly, [switch]$LibraryOnly, [Parameter(ValueFromRemainingArguments=$true)][string[]]$Options)
$ErrorActionPreference = 'Stop'
$mode = if ($Options -contains '--install') { '--install' } else { '--run' }
Set-Location -LiteralPath $PSScriptRoot
[Console]::OutputEncoding = [Text.UTF8Encoding]::new()
foreach ($name in 'PYTHONPATH','PYTHONHOME','TCL_LIBRARY','TK_LIBRARY') {
    [Environment]::SetEnvironmentVariable($name, $null, 'Process')
}
function Say([string]$ru, [string]$en) {
    Write-Host $ru
    Write-Host $en
}
function Test-Python([string]$Path) {
    if (-not $Path -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
    # A script file avoids the native-command quote loss in Windows PowerShell 5.1.
    $ErrorActionPreference = 'Continue'
    $result = & $Path -E (Join-Path $PSScriptRoot 'gacha_python_probe.py') 2>$null
    return ($LASTEXITCODE -eq 0)
}
function Find-Python {
    $ErrorActionPreference = 'Continue'
    $candidates = @((Join-Path $PSScriptRoot '.venv\Scripts\python.exe'))
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        $lines = & $launcher.Source -0p 2>$null
        foreach ($line in $lines) {
            if ($line -match '([A-Za-z]:\\.*python(?:w)?\.exe)\s*$') { $candidates += $Matches[1].Trim() }
        }
    }
    foreach ($registry in 'HKCU:\Software\Python\PythonCore','HKLM:\Software\Python\PythonCore') {
        foreach ($version in (Get-ChildItem -LiteralPath $registry -ErrorAction SilentlyContinue)) {
            $install = Get-Item -LiteralPath ($version.PSPath+'\InstallPath') -ErrorAction SilentlyContinue
            if ($install) {
                $executable = $install.GetValue('ExecutablePath')
                if ($executable) { $candidates += $executable }
                $directory = $install.GetValue('')
                if ($directory) { $candidates += (Join-Path $directory 'python.exe') }
            }
        }
    }
    foreach ($base in @("$env:LOCALAPPDATA\Programs\Python", "$env:ProgramFiles", 'C:\')) {
        foreach ($folder in (Get-ChildItem -LiteralPath $base -Directory -Filter 'Python3*' -ErrorAction SilentlyContinue)) {
            $candidates += (Join-Path $folder.FullName 'python.exe')
        }
    }
    foreach ($command in (Get-Command python.exe,python3.exe -All -ErrorAction SilentlyContinue)) {
        if ($command.Source -notlike '*\WindowsApps\*') { $candidates += $command.Source }
    }
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (Test-Python $candidate) { return $candidate }
    }
    return $null
}
function Install-OfficialPython {
    Say 'Загружаю официальный Python с Tcl/Tk. Права администратора обычно не нужны.' 'Downloading official Python with Tcl/Tk. Administrator rights are normally not required.'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $download = Join-Path ([IO.Path]::GetTempPath()) ('gacha-python-'+[Guid]::NewGuid().ToString('N')+'.exe')
    try {
        Invoke-WebRequest -UseBasicParsing -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile $download
        $signature = Get-AuthenticodeSignature -LiteralPath $download
        if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Python Software Foundation') {
            throw 'Не удалось проверить подпись установщика / Installer signature verification failed.'
        }
        $installArgs = '/quiet InstallAllUsers=0 Include_tcltk=1 Include_pip=1 Include_test=0 Include_launcher=0 PrependPath=0'
        if (Test-Path -LiteralPath "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe") { $installArgs = '/modify '+$installArgs }
        $process = Start-Process -FilePath $download -ArgumentList $installArgs -WindowStyle Hidden -Wait -PassThru
        # Discovery, not an installer exit code, determines whether launching is possible.
        return $process.ExitCode
    } finally {
        Remove-Item -LiteralPath $download -Force -ErrorAction SilentlyContinue
    }
}
function Ensure-Python {
    $pythonPath = Find-Python
    if ($pythonPath) { return $pythonPath }
    Say 'Подготавливаю Python. При первом запуске нужен интернет.' 'Preparing Python. Internet is required for first-time setup.'
    if (Get-Command winget.exe -ErrorAction SilentlyContinue) {
        $previousPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            & winget.exe install --id Python.Python.3.12 --exact --source winget --scope user --silent --accept-package-agreements --accept-source-agreements | Out-Host
        } finally { $ErrorActionPreference = $previousPreference }
        # WinGet returns a nonzero code for an already installed/current package too.
        $pythonPath = Find-Python
        if ($pythonPath) { return $pythonPath }
    }
    $code = Install-OfficialPython
    $pythonPath = Find-Python
    if ($pythonPath) { return $pythonPath }
    throw "Python с Tcl/Tk недоступен после установки (код $code). Установите Python 3.12 x64 с Tcl/Tk с python.org. / Python with Tcl/Tk is unavailable after setup (code $code). Install Python 3.12 x64 with Tcl/Tk from python.org."
}
if ($LibraryOnly) { return }
try {
    if ($CheckOnly) {
        $pythonPath = Find-Python
        if ($pythonPath) { Write-Host $pythonPath; exit 0 }
        exit 1
    }
    $pythonPath = Ensure-Python
    & $pythonPath -E (Join-Path $PSScriptRoot 'gacha_bootstrap.py') $mode
    exit $LASTEXITCODE
} catch {
    Write-Host $_ -ForegroundColor Red
    Say 'Не удалось подготовить запуск. Проверьте интернет и повторите run_skin_gacha.cmd. Подробности: HOW_TO_RUN.txt.' 'Setup could not finish. Check your connection and retry run_skin_gacha.cmd. See HOW_TO_RUN.txt.'
    exit 1
}
