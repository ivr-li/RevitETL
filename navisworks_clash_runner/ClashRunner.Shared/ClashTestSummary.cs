using System.Collections.Generic;

namespace ClashRunner.Shared
{
    public class ClashTestSummary
    {
        public string TestName { get; set; }
        public string TestType { get; set; }
        public string TestStatus { get; set; }
        public int TotalClashes { get; set; }
        public int NewCount { get; set; }
        public int ActiveCount { get; set; }
        public int ReviewedCount { get; set; }
        public int ApprovedCount { get; set; }
        public int ResolvedCount { get; set; }
        public List<ClashResultEntry> Results { get; set; } = new List<ClashResultEntry>();
    }
}
