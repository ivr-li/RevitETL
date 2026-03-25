@echo off
REM Deploy ClashRunner plugin to Navisworks ApplicationPlugins

set BUILD_DIR=%~dp0ClashRunner.Plugin\bin\Release

REM Deploy to user-level ApplicationPlugins
set BUNDLE_DIR=%AppData%\Autodesk\ApplicationPlugins\ClashRunner.bundle
call :deploy_to "%BUNDLE_DIR%"

REM Deploy to system-level ApplicationPlugins (needed for Automation API)
set BUNDLE_DIR=%ProgramData%\Autodesk\ApplicationPlugins\ClashRunner.bundle
call :deploy_to "%BUNDLE_DIR%"

echo Done. Restart Navisworks to load the plugin.
exit /b 0

:deploy_to
set TARGET=%~1
set TARGET_CONTENTS=%TARGET%\Contents
echo Deploying ClashRunner to %TARGET%...
if not exist "%TARGET_CONTENTS%" mkdir "%TARGET_CONTENTS%"
copy /Y "%~dp0PackageContents.xml" "%TARGET%\PackageContents.xml"
copy /Y "%BUILD_DIR%\ClashRunner.Plugin.dll" "%TARGET_CONTENTS%\"
copy /Y "%BUILD_DIR%\ClashRunner.Shared.dll" "%TARGET_CONTENTS%\"
exit /b 0
