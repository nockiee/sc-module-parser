@echo off
setlocal enabledelayedexpansion

set "ROOT=%~dp0"
pushd "%ROOT%"

set "PYTHON="
where python >nul 2>nul && set "PYTHON=python"
if not defined PYTHON (
    where py >nul 2>nul && set "PYTHON=py -3"
)
if not defined PYTHON (
    echo Python was not found in PATH.
    popd
    exit /b 1
)

%PYTHON% -m pip --version >nul 2>nul
if errorlevel 1 (
    echo pip is not available. Trying to bootstrap it...
    %PYTHON% -m ensurepip --upgrade
    if errorlevel 1 (
        echo Failed to bootstrap pip.
        popd
        exit /b 1
    )
)

if exist requirements.txt (
    echo Installing dependencies from requirements.txt...
    %PYTHON% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Dependency installation failed.
        popd
        exit /b 1
    )
)

%PYTHON% use_cli.py %*
set "EXITCODE=%ERRORLEVEL%"

popd
exit /b %EXITCODE%
