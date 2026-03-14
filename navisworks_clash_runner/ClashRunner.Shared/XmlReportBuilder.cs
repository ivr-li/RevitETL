using System.Collections.Generic;
using System.Globalization;
using System.Xml;

namespace ClashRunner.Shared
{
    public static class XmlReportBuilder
    {
        private static readonly CultureInfo Inv = CultureInfo.InvariantCulture;

        public static void Build(List<ClashTestSummary> summaries, string outputPath)
        {
            var settings = new XmlWriterSettings
            {
                Indent = true,
                Encoding = System.Text.Encoding.UTF8
            };

            using (var writer = XmlWriter.Create(outputPath, settings))
            {
                writer.WriteStartDocument();
                WriteExchange(writer, summaries);
                writer.WriteEndDocument();
            }
        }

        private static void WriteExchange(
            XmlWriter w, List<ClashTestSummary> summaries)
        {
            w.WriteStartElement("exchange");
            w.WriteAttributeString("xmlns", "xsi", null,
                "http://www.w3.org/2001/XMLSchema-instance");
            w.WriteAttributeString("units", "m");
            w.WriteAttributeString("filename", "");
            w.WriteAttributeString("filepath", "");

            WriteBatchTest(w, summaries);

            w.WriteEndElement();
        }

        private static void WriteBatchTest(
            XmlWriter w, List<ClashTestSummary> summaries)
        {
            w.WriteStartElement("batchtest");
            w.WriteAttributeString("name", "Report");
            w.WriteAttributeString("internal_name", "Report");
            w.WriteAttributeString("units", "m");

            w.WriteStartElement("clashtests");
            foreach (var summary in summaries)
                WriteClashTest(w, summary);
            w.WriteEndElement();

            w.WriteStartElement("selectionsets");
            w.WriteEndElement();

            w.WriteEndElement();
        }

        private static void WriteClashTest(XmlWriter w, ClashTestSummary summary)
        {
            w.WriteStartElement("clashtest");
            w.WriteAttributeString("name", summary.TestName);
            w.WriteAttributeString("test_type", "hard");
            w.WriteAttributeString("status", summary.TestStatus ?? "ok");

            WriteSummary(w, summary);
            WriteClashResults(w, summary.Results);

            w.WriteEndElement();
        }

        private static void WriteSummary(XmlWriter w, ClashTestSummary s)
        {
            w.WriteStartElement("summary");
            w.WriteAttributeString("total", s.TotalClashes.ToString(Inv));
            w.WriteAttributeString("new", s.NewCount.ToString(Inv));
            w.WriteAttributeString("active", s.ActiveCount.ToString(Inv));
            w.WriteAttributeString("reviewed", s.ReviewedCount.ToString(Inv));
            w.WriteAttributeString("approved", s.ApprovedCount.ToString(Inv));
            w.WriteAttributeString("resolved", s.ResolvedCount.ToString(Inv));
            w.WriteElementString("testtype", s.TestType ?? "");
            w.WriteElementString("teststatus", s.TestStatus ?? "");
            w.WriteEndElement();
        }

        private static void WriteClashResults(
            XmlWriter w, List<ClashResultEntry> results)
        {
            w.WriteStartElement("clashresults");

            foreach (var r in results)
                WriteClashResult(w, r);

            w.WriteEndElement();
        }

        private static void WriteClashResult(XmlWriter w, ClashResultEntry r)
        {
            w.WriteStartElement("clashresult");
            w.WriteAttributeString("name", r.ClashName);
            w.WriteAttributeString("guid", r.Guid ?? "");
            w.WriteAttributeString("status", r.Status);
            w.WriteAttributeString("distance", r.Distance.ToString("F3", Inv));

            w.WriteElementString("description", r.Description ?? "");
            w.WriteElementString("resultstatus", r.StatusLocalized ?? "");

            WriteClashPoint(w, r);
            WriteCreatedDate(w, r);
            WriteClashObjects(w, r.ClashObjects);

            w.WriteEndElement();
        }

        private static void WriteClashPoint(XmlWriter w, ClashResultEntry r)
        {
            w.WriteStartElement("clashpoint");
            w.WriteStartElement("pos3f");
            w.WriteAttributeString("x", r.X.ToString("F3", Inv));
            w.WriteAttributeString("y", r.Y.ToString("F3", Inv));
            w.WriteAttributeString("z", r.Z.ToString("F3", Inv));
            w.WriteEndElement();
            w.WriteEndElement();
        }

        private static void WriteCreatedDate(XmlWriter w, ClashResultEntry r)
        {
            var d = r.CreatedDate;
            w.WriteStartElement("createddate");
            w.WriteStartElement("date");
            w.WriteAttributeString("year", d.Year.ToString(Inv));
            w.WriteAttributeString("month", d.Month.ToString(Inv));
            w.WriteAttributeString("day", d.Day.ToString(Inv));
            w.WriteAttributeString("hour", d.Hour.ToString(Inv));
            w.WriteAttributeString("minute", d.Minute.ToString(Inv));
            w.WriteAttributeString("second", d.Second.ToString(Inv));
            w.WriteEndElement();
            w.WriteEndElement();
        }

        private static void WriteClashObjects(
            XmlWriter w, List<ClashObjectInfo> objects)
        {
            w.WriteStartElement("clashobjects");

            foreach (var obj in objects)
                WriteClashObject(w, obj);

            w.WriteEndElement();
        }

        private static void WriteClashObject(XmlWriter w, ClashObjectInfo obj)
        {
            w.WriteStartElement("clashobject");

            w.WriteStartElement("objectattribute");
            w.WriteElementString("name", "ID объекта");
            w.WriteElementString("value", obj.ObjectId ?? "");
            w.WriteEndElement();

            w.WriteStartElement("smarttags");
            foreach (var tag in obj.SmartTags)
            {
                w.WriteStartElement("smarttag");
                w.WriteElementString("name", tag.Name);
                w.WriteElementString("value", tag.Value ?? "");
                w.WriteEndElement();
            }
            w.WriteEndElement();

            w.WriteEndElement();
        }
    }
}
