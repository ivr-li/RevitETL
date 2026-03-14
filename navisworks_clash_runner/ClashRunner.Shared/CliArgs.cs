namespace ClashRunner.Shared
{
    public class CliArgs
    {
        public string NwdDirectory { get; set; }
        public string NwfPath { get; set; }
        public string ClashSettingsXml { get; set; }
        public string OutputDirectory { get; set; }

        public static CliArgs Parse(string[] args)
        {
            var result = new CliArgs();

            for (int i = 0; i < args.Length - 1; i++)
            {
                switch (args[i])
                {
                    case "--nwd-dir":
                        result.NwdDirectory = args[++i];
                        break;
                    case "--nwf":
                        result.NwfPath = args[++i];
                        break;
                    case "--clash-settings":
                        result.ClashSettingsXml = args[++i];
                        break;
                    case "--output":
                        result.OutputDirectory = args[++i];
                        break;
                }
            }

            return result;
        }

        public string Validate()
        {
            if (string.IsNullOrEmpty(NwdDirectory) && string.IsNullOrEmpty(NwfPath))
                return "Either --nwd-dir or --nwf must be specified.";

            if (string.IsNullOrEmpty(OutputDirectory))
                return "--output is required.";

            return null;
        }
    }
}
