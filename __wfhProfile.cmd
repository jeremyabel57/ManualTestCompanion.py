@echo off
echo.
echo.
echo.
echo.
if defined HTTP_PROXY (
:: switch from internal profile to external profile
echo Switching to external profile
setx HTTP_PROXY_ "%HTTP_PROXY%" >nul 2>&1
set "HTTP_PROXY_=%HTTP_PROXY%"
set HTTP_PROXY=
reg delete "HKCU\Environment" /F /V "HTTP_PROXY" >nul 2>&1
setx HTTPS_PROXY_ "%HTTPS_PROXY%" >nul 2>&1
set "HTTPS_PROXY_=%HTTPS_PROXY%"
set HTTPS_PROXY=
reg delete "HKCU\Environment" /F /V "HTTPS_PROXY" >nul 2>&1

git config --global --unset http.proxy
git config --global --unset https.proxy
git config --global --unset http.https://github.com.proxy
git config --global --unset http.https://lfs.github.com.proxy
git config --global --unset http.https://github-cloud.s3.amazonaws.com.proxy
git config --global --unset http.https://github-cloud.githubusercontent.com.proxy

) else (
:: swtich from external profile to internal profile
echo Switching to internal profile
setx HTTP_PROXY "%HTTP_PROXY_%" >nul 2>&1
set "HTTP_PROXY=%HTTP_PROXY_%"
set HTTP_PROXY_=
reg delete "HKCU\Environment" /F /V "HTTP_PROXY_" >nul 2>&1
setx HTTPS_PROXY "%HTTPS_PROXY_%" >nul 2>&1
set "HTTPS_PROXY=%HTTPS_PROXY_%"
set HTTPS_PROXY_=
reg delete "HKCU\Environment" /F /V "HTTPS_PROXY_" >nul 2>&1

git config --global --add http.proxy http://proxy-dmz.intel.com:912
git config --global --add https.proxy http://proxy-dmz.intel.com:912
git config --global --add http.https://github.com.proxy http://proxy-dmz.intel.com:912
git config --global --add http.https://lfs.github.com.proxy http://proxy-dmz.intel.com:912
git config --global --add http.https://github-cloud.s3.amazonaws.com.proxy http://proxy-dmz.intel.com:912
git config --global --add http.https://github-cloud.githubusercontent.com.proxy http://proxy-dmz.intel.com:912

)


timeout /t 1 >nul 2>&1
echo.
echo.

echo HTTPS_PROXY = %HTTPS_PROXY%
echo HTTPS_PROXY_ = %HTTPS_PROXY_%
git config --global -l

timeout /t 5
