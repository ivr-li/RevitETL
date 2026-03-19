using System;
using System.IO;
using System.Linq;
using Autodesk.Navisworks.Api.Automation;
using ClashRunner.Shared;

namespace ClashRunner.Automation
{
    internal class Program
    {
        private const string PluginId = "ADSK.ClashRunner.Plugin.ClashRunnerAddIn";
        private const string NwfFileName = "Проверка пересечений.nwf";

        static int Main(string[] args)
        {
            var cli = CliArgs.Parse(args);
            var error = cli.Validate();

            if (error != null)
            {
                Console.Error.WriteLine(error);
                PrintUsage();
                return 1;
            }

            try
            {
                RunClashWorkflow(cli);
                return 0;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"Fatal: {ex.Message}");
                Console.Error.WriteLine(ex.StackTrace);
                return 2;
            }
        }

        private static void RunClashWorkflow(CliArgs cli)
        {
            using (var navis = new NavisworksApplication())
            {
                string nwfPath = ResolveNwfPath(cli);

                if (File.Exists(nwfPath))
                {
                    Console.WriteLine($"Opening existing NWF: {nwfPath}");
                    navis.OpenFile(nwfPath);
                }
                else
                {
                    LoadNwdFiles(navis, cli.NwdDirectory);
                }

                // Pass args as semicolon-delimited string
                string pluginArgs = string.Join(";",
                    cli.ClashSettingsXml ?? "",
                    cli.OutputDirectory,
                    nwfPath);

                Console.WriteLine("Executing clash plugin...");
                navis.ExecuteAddInPlugin(PluginId, pluginArgs);

                Console.WriteLine($"Saving NWF: {nwfPath}");
                navis.SaveFile(nwfPath);
            }

            Console.WriteLine("Done.");
        }

        private static string ResolveNwfPath(CliArgs cli)
        {
            if (!string.IsNullOrEmpty(cli.NwfPath))
                return cli.NwfPath;

            return Path.Combine(cli.NwdDirectory, NwfFileName);
        }

        private static void LoadNwdFiles(NavisworksApplication navis, string nwdDir)
        {
            var nwdFiles = Directory.GetFiles(nwdDir, "*.nwd")
                .OrderBy(f => f)
                .ToArray();

            if (nwdFiles.Length == 0)
                throw new FileNotFoundException($"No .nwd files found in {nwdDir}");

            Console.WriteLine($"Loading {nwdFiles.Length} NWD files from {nwdDir}");

            navis.OpenFile(nwdFiles[0]);

            for (int i = 1; i < nwdFiles.Length; i++)
            {
                Console.WriteLine($"  Appending: {Path.GetFileName(nwdFiles[i])}");
                navis.AppendFile(nwdFiles[i]);
            }
        }

        private static void PrintUsage()
        {
            Console.WriteLine();
            Console.WriteLine("Usage: ClashRunner.Automation.exe [options]");
            Console.WriteLine();
            Console.WriteLine("Options:");
            Console.WriteLine("  --nwd-dir <path>         Directory with .nwd files");
            Console.WriteLine("  --nwf <path>             Path to existing .nwf file (optional)");
            Console.WriteLine("  --clash-settings <path>  Clash test definitions XML (optional)");
            Console.WriteLine("  --output <path>          Output directory for reports");
        }
    }
}
