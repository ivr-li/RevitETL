@echo off
REM Deploy ClashRunner plugin to Navisworks ApplicationPlugins

set BUNDLE_DIR=%AppData%\Autodesk\ApplicationPlugins\ClashRunner.bundle
set CONTENTS_DIR=%BUNDLE_DIR%\Contents
set BUILD_DIR=%~dp0ClashRunner.Plugin\bin\Release

echo Deploying ClashRunner to %BUNDLE_DIR%...

if not exist "%CONTENTS_DIR%" mkdir "%CONTENTS_DIR%"

copy /Y "%~dp0PackageContents.xml" "%BUNDLE_DIR%\PackageContents.xml"
copy /Y "%BUILD_DIR%\ClashRunner.Plugin.dll" "%CONTENTS_DIR%\"
copy /Y "%BUILD_DIR%\ClashRunner.Shared.dll" "%CONTENTS_DIR%\"

echo Done. Restart Navisworks to load the plugin.
