@echo off

start "Test" ^
 "C:\Users\medvedev\Desktop\RevitETL\navisworks_clash_runner\ClashRunner.Automation\bin\Release\net47\ClashRunner.Automation.exe" ^
 --nwd-dir "\\fs\bim\Projects\00.BIM_Export\Export_nwd\03. NWD folders\NBR_TGN_GP03" ^
 --nwf "\\fs\bim\Projects\00.BIM_Export\Export_nwd\03. NWD folders\NBR_TGN_GP03\NBR_TGN_GP03_Проверка на пересечения.nwf" ^
 --output "\\fs\bim\Projects\00.BIM_Export\Export_nwd\03. NWD folders\NBR_TGN_GP03\autotest"

echo ----------
