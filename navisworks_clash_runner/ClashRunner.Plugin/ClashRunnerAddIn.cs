using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Autodesk.Navisworks.Api;
using Autodesk.Navisworks.Api.Clash;
using Autodesk.Navisworks.Api.Plugins;
using ClashRunner.Shared;

namespace ClashRunner.Plugin
{
    [PluginAttribute("ClashRunner.Plugin.ClashRunnerAddIn",
        "ADSK",
        DisplayName = "Clash Runner",
        ToolTip = "Runs clash tests and exports results")]
    [AddInPluginAttribute(AddInLocation.None)]
    public class ClashRunnerAddIn : AddInPlugin
    {
        public override int Execute(params string[] parameters)
        {
            // Args: "clashSettingsXml;outputDir;nwfPath"
            var parts = parameters[0].Split(';');
            string clashSettingsXml = parts[0];
            string outputDir = parts[1];

            try
            {
                var doc = Application.ActiveDocument;
                var clash = doc.GetClash();

                ImportClashSettings(clash, clashSettingsXml);
                RunAllTests(clash);

                var summaries = CollectResults(clash);
                ExportResults(summaries, outputDir);

                return 0;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"Plugin error: {ex.Message}");
                return 1;
            }
        }

        private static void ImportClashSettings(DocumentClash clash, string xmlPath)
        {
            if (string.IsNullOrEmpty(xmlPath) || !File.Exists(xmlPath))
            {
                Console.WriteLine("No clash settings XML — using existing tests.");
                return;
            }

            Console.WriteLine($"Importing clash settings from: {xmlPath}");
            clash.TestsData.TestsImportXml(xmlPath);
        }

        private static void RunAllTests(DocumentClash clash)
        {
            var tests = GetClashTests(clash);

            Console.WriteLine($"Running {tests.Count} clash tests...");

            foreach (var test in tests)
            {
                Console.WriteLine($"  Running: {test.DisplayName}");
                clash.TestsData.TestsRunTest(test);
            }
        }

        private static List<ClashTest> GetClashTests(DocumentClash clash)
        {
            return clash.TestsData.Tests
                .OfType<ClashTest>()
                .ToList();
        }

        private static List<ClashTestSummary> CollectResults(DocumentClash clash)
        {
            var tests = GetClashTests(clash);
            var summaries = new List<ClashTestSummary>();

            foreach (var test in tests)
            {
                var summary = BuildSummary(test);
                summaries.Add(summary);

                Console.WriteLine(
                    $"  {test.DisplayName}: {summary.TotalClashes} clashes " +
                    $"(New={summary.NewCount}, Active={summary.ActiveCount})");
            }

            return summaries;
        }

        private static ClashTestSummary BuildSummary(ClashTest test)
        {
            var summary = new ClashTestSummary { TestName = test.DisplayName };

            foreach (var item in test.Children)
            {
                ProcessClashItem(item, test.DisplayName, summary);
            }

            summary.TotalClashes = summary.Results.Count;
            return summary;
        }

        private static void ProcessClashItem(
            SavedItem item, string testName, ClashTestSummary summary)
        {
            if (item is ClashResultGroup group)
            {
                foreach (var child in group.Children)
                    ProcessClashItem(child, testName, summary);
                return;
            }

            if (!(item is ClashResult result))
                return;

            var entry = MapResultToEntry(result, testName);
            summary.Results.Add(entry);
            IncrementStatusCounter(summary, result.Status);
        }

        private static ClashResultEntry MapResultToEntry(
            ClashResult result, string testName)
        {
            var point = result.Center;

            return new ClashResultEntry
            {
                TestName = testName,
                ClashName = result.DisplayName,
                Status = result.Status.ToString(),
                X = point.X,
                Y = point.Y,
                Z = point.Z,
                Distance = result.Distance,
                Item1Path = GetItemPath(result.CompositeItem1),
                Item2Path = GetItemPath(result.CompositeItem2),
                Item1Layer = GetItemLayer(result.CompositeItem1),
                Item2Layer = GetItemLayer(result.CompositeItem2),
                GridLocation = result.GridIntersect ?? ""
            };
        }

        private static void IncrementStatusCounter(
            ClashTestSummary summary, ClashResultStatus status)
        {
            switch (status)
            {
                case ClashResultStatus.New:
                    summary.NewCount++;
                    break;
                case ClashResultStatus.Active:
                    summary.ActiveCount++;
                    break;
                case ClashResultStatus.Reviewed:
                    summary.ReviewedCount++;
                    break;
                case ClashResultStatus.Approved:
                    summary.ApprovedCount++;
                    break;
                case ClashResultStatus.Resolved:
                    summary.ResolvedCount++;
                    break;
            }
        }

        private static string GetItemPath(ModelItem item)
        {
            if (item == null)
                return "";

            var parts = new List<string>();
            var current = item;

            while (current != null)
            {
                if (!string.IsNullOrEmpty(current.DisplayName))
                    parts.Insert(0, current.DisplayName);
                current = current.Parent;
            }

            return string.Join(" > ", parts);
        }

        private static string GetItemLayer(ModelItem item)
        {
            if (item == null)
                return "";

            var cat = item.PropertyCategories
                .FindCategoryByDisplayName("Element");

            if (cat == null)
                return "";

            var prop = cat.Properties
                .FindPropertyByDisplayName("Layer");

            return prop?.Value?.ToDisplayString() ?? "";
        }

        private static void ExportResults(
            List<ClashTestSummary> summaries, string outputDir)
        {
            Directory.CreateDirectory(outputDir);
            string xmlPath = Path.Combine(outputDir, "clash_report.xml");

            Console.WriteLine($"Exporting report to: {xmlPath}");
            XmlReportBuilder.Build(summaries, xmlPath);
        }
    }
}
