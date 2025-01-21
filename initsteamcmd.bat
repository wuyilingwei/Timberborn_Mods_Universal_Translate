echo [Init info] Initializate SteamCMD
mkdir steamcmd >nul 2>&1
cd steamcmd
curl -s https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip -o steamcmd.zip
tar -xf steamcmd.zip
del /q steamcmd.zip
steamcmd +quit

echo [Init info] Initializated SteamCMD
echo [Init info] Done! Environment is ready.
echo [Init info] Check the logs for any errors. Next step will start in 5 seconds.

echo [Init info] Steam username? This account must have Timberborn workshop access permissions.(Purchased or Famliy Share)
set /p steam_username=
echo [Init info] We will try to login to Steam in 5 seconds
echo [Init info] If you have Steam Guard enabled, you will need to enter the two-factor code
echo [Init info] It can find in your email or in your phone show the code
echo [Init info] This is a one-time process, your password will not be saved
timeout /t 5 /nobreak >nul
steamcmd +login %steam_username% +quit