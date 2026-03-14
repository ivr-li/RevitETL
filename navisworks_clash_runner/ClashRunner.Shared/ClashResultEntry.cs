namespace ClashRunner.Shared
{
    public class ClashResultEntry
    {
        public string TestName { get; set; }
        public string ClashName { get; set; }
        public string Status { get; set; }
        public double X { get; set; }
        public double Y { get; set; }
        public double Z { get; set; }
        public string Item1Path { get; set; }
        public string Item2Path { get; set; }
        public string Item1Layer { get; set; }
        public string Item2Layer { get; set; }
        public double Distance { get; set; }
        public string GridLocation { get; set; }
    }
}
