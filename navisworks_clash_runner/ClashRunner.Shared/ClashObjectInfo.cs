using System.Collections.Generic;

namespace ClashRunner.Shared
{
    public class ClashObjectInfo
    {
        public string ObjectId { get; set; }
        public List<SmartTag> SmartTags { get; set; } = new List<SmartTag>();
    }
}
