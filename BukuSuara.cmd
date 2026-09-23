@echo off
setlocal
cd /d "%~dp0"
title BukuSuara Studio
call ebook2audiobook.cmd %*
set EXIT_CODE=%ERRORLEVEL%
endlocal & exit /b %EXIT_CODE%
