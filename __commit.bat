@echo off
echo.
echo.
echo.
call _bcompSync.bat
move /y Backup\*.* ..\_backup
::move archive ..\_archive
git status
echo.
set /p c=Commit Note:^ 
echo.
git add .
git commit -a -m "%c%"
echo.
git push
echo.
::move ..\_backup Backup
::move ..\_archive archive
timeout /t 5
