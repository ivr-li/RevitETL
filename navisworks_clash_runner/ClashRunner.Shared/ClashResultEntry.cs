using System;
using System.Collections.Generic;

namespace ClashRunner.Shared
{
    public class ClashResultEntry
    {
        public string TestName { get; set; }
        public string ClashName { get; set; }
        public string Guid { get; set; }
        public string Status { get; set; }
        public string StatusLocalized { get; set; }
        public string Description { get; set; }
        public double X { get; set; }
        public double Y { get; set; }
        public double Z { get; set; }
        public double Distance { get; set; }
        public DateTime CreatedDate { get; set; }
        public List<ClashObjectInfo> ClashObjects { get; set; } = new List<ClashObjectInfo>();
    }
}
