# ClashRunner — Build & Deploy

## Prerequisites

- Visual Studio 2019+ with .NET Framework 4.7 targeting pack
- Autodesk Navisworks Manage 2022 installed (for API DLLs)

## Build

```bash
# From solution root
msbuild NavisworksClashRunner.sln /p:Configuration=Release
```

Or open `NavisworksClashRunner.sln` in Visual Studio and build Release.

## Deploy Plugin

```bash
deploy.bat
```

This copies `ClashRunner.Plugin.dll` + `ClashRunner.Shared.dll` to:
`%AppData%\Autodesk\ApplicationPlugins\ClashRunner.bundle\`

## Usage

```bash
ClashRunner.Automation.exe ^
  --nwd-dir "\\fs\bim\Projects\KGN_GP5.2\01_NWD" ^
  --clash-settings "\\fs\bim\Templates\clash_tests.xml" ^
  --output "\\fs\bim\Projects\KGN_GP5.2\02_Collisions"
```

### Arguments

| Arg | Required | Description |
|-----|----------|-------------|
| `--nwd-dir` | Yes* | Directory containing .nwd files to load |
| `--nwf` | Yes* | Path to existing .nwf (skips NWD loading) |
| `--clash-settings` | No | Clash test definitions XML to import |
| `--output` | Yes | Directory for clash reports |

*Either `--nwd-dir` or `--nwf` must be specified.

### Workflow

1. If `Проверка пересечений.nwf` exists (or `--nwf` specified) — opens it directly
2. Otherwise — loads all `.nwd` from `--nwd-dir`, appends into one document
3. Imports clash test settings from XML (if `--clash-settings` provided)
4. Runs all clash tests
5. Exports results to `--output`
6. Saves the document as `.nwf` for reuse
