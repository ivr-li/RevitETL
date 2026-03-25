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
    [PluginAttribute("ClashRunnerAddIn",
        "ADSK",
        DisplayName = "Clash Runner",
        ToolTip = "Runs clash tests and exports results")]
    [AddInPluginAttribute(AddInLocation.None)]
    public class ClashRunnerAddIn : AddInPlugin
    {
        // Smart tag definitions matching 03_Быстрый показ свойств.xml
        private static readonly string[][] SmartTagDefs =
        {
            new[] { "LcOaXRefAttribute", "LcOaXRefAttributePath", "Внешняя ссылка Путь" },
            new[] { "LcRevitData_Element", "LcRevitPropertyElementId", "Объект Id" },
            new[] { "LcRevitData_Element", "lcldrevit_parameter_ADSK_????? ??????_PG_DATA", "Объект ADSK_Номер секции" },
            new[] { "LcOaNode", "LcOaSceneBaseUserName", "Элемент Имя" },
            new[] { "LcRevitData_Element", "lcldrevit_parameter_-1002053", "Объект Рабочий набор" },
        };

        private static readonly Dictionary<ClashResultStatus, string> StatusNames =
            new Dictionary<ClashResultStatus, string>
            {
                { ClashResultStatus.New, "Создать" },
                { ClashResultStatus.Active, "Активно" },
                { ClashResultStatus.Reviewed, "Проверено" },
                { ClashResultStatus.Approved, "Подтверждено" },
                { ClashResultStatus.Resolved, "Исправлено" },
            };

        public override int Execute(params string[] parameters)
        {
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

        private static void ImportClashSettings(DocumentClash clash, string templatePath)
        {
            if (string.IsNullOrEmpty(templatePath) || !File.Exists(templatePath))
            {
                Console.WriteLine("No clash template — using existing tests.");
                return;
            }

            // TODO: implement clash test import from template
            // Navisworks 2022 API does not have XML import for clash tests.
            // Options: load tests from a template .nwf via TestsAddCopy,
            // or build ClashTest objects programmatically.
            Console.WriteLine($"Clash template provided: {templatePath} (import not yet implemented)");
        }

        private static void RunAllTests(DocumentClash clash)
        {
            var tests = GetClashTests(clash);
            Console.WriteLine($"Running {tests.Count} clash tests...");
            clash.TestsData.TestsRunAllTests();
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
            var summary = new ClashTestSummary
            {
                TestName = test.DisplayName,
                TestType = test.TestType.ToString(),
                TestStatus = test.Status.ToString(),
            };

            foreach (var item in test.Children)
                ProcessClashItem(item, test.DisplayName, summary);

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
            var statusName = StatusNames.ContainsKey(result.Status)
                ? StatusNames[result.Status]
                : result.Status.ToString();

            return new ClashResultEntry
            {
                TestName = testName,
                ClashName = result.DisplayName,
                Guid = result.Guid.ToString(),
                Status = result.Status.ToString().ToLowerInvariant(),
                StatusLocalized = statusName,
                Description = result.Description ?? "",
                X = point.X,
                Y = point.Y,
                Z = point.Z,
                Distance = result.Distance,
                CreatedDate = result.CreatedTime?.ToLocalTime() ?? DateTime.MinValue,
                ClashObjects = BuildClashObjects(result),
            };
        }

        private static List<ClashObjectInfo> BuildClashObjects(ClashResult result)
        {
            var objects = new List<ClashObjectInfo>();
            AddClashObject(objects, result.CompositeItem1);
            AddClashObject(objects, result.CompositeItem2);
            return objects;
        }

        private static void AddClashObject(
            List<ClashObjectInfo> objects, ModelItem item)
        {
            if (item == null)
                return;

            var obj = new ClashObjectInfo
            {
                ObjectId = GetElementId(item),
                SmartTags = ExtractSmartTags(item),
            };
            objects.Add(obj);
        }

        private static string GetElementId(ModelItem item)
        {
            var cat = item.PropertyCategories
                .FindCategoryByName("LcRevitData_Element");

            if (cat == null)
                return "";

            var prop = cat.Properties
                .FindPropertyByName("LcRevitPropertyElementId");

            return prop?.Value?.ToDisplayString() ?? "";
        }

        private static List<SmartTag> ExtractSmartTags(ModelItem item)
        {
            var tags = new List<SmartTag>();

            foreach (var def in SmartTagDefs)
            {
                string catName = def[0];
                string propName = def[1];
                string displayName = def[2];

                string value = GetPropertyValue(item, catName, propName);
                tags.Add(new SmartTag { Name = displayName, Value = value });
            }

            return tags;
        }

        private static string GetPropertyValue(
            ModelItem item, string categoryName, string propertyName)
        {
            if (item == null)
                return "";

            var cat = item.PropertyCategories.FindCategoryByName(categoryName);
            if (cat == null)
                return "";

            var prop = cat.Properties.FindPropertyByName(propertyName);
            return prop?.Value?.ToDisplayString() ?? "";
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
