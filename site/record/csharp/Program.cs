// Reads URLs with .NET's System.Uri, for site/record/record.py.
//
// Each input line is base64 of the input, a space, and base64 of the base
// (or "-" for none). Prints one JSON line per input line.
// Run: dotnet run

using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;

if (args.Length > 0 && args[0] == "--version")
{
    Console.WriteLine($".NET {Environment.Version}");
    return;
}

var options = new JsonSerializerOptions { Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping };
string Decode(string text) => Encoding.UTF8.GetString(Convert.FromBase64String(text));

Dictionary<string, object?> Parse(string input, string? baseText)
{
    try
    {
        var uri = baseText is null ? new Uri(input, UriKind.Absolute) : new Uri(new Uri(baseText, UriKind.Absolute), input);
        // IdnHost is the host an HTTP client connects to: international
        // names in ASCII.
        string? host = uri.HostNameType == UriHostNameType.Unknown && uri.IdnHost == "" ? null : uri.IdnHost;
        return new() { ["ok"] = true, ["scheme"] = uri.Scheme, ["host"] = host, ["path"] = uri.AbsolutePath, ["href"] = uri.AbsoluteUri };
    }
    catch (Exception e)
    {
        return new() { ["ok"] = false, ["error"] = $"{e.GetType().Name}: {e.Message}" };
    }
}

Console.OutputEncoding = new UTF8Encoding(false);
string? line;
while ((line = Console.In.ReadLine()) is not null)
{
    var parts = line.Split(' ');
    var input = Decode(parts[0]);
    string? baseText = parts[1] == "-" ? null : Decode(parts[1]);
    Console.WriteLine(JsonSerializer.Serialize(new Dictionary<string, object> { ["csharp"] = Parse(input, baseText) }, options));
}
