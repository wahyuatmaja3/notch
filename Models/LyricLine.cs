using System;

namespace Notch.Models;

public class LyricLine
{
    public TimeSpan Timestamp { get; set; }
    public double Milliseconds => Timestamp.TotalMilliseconds;
    public string Text { get; set; } = string.Empty;

    public LyricLine() { }

    public LyricLine(TimeSpan timestamp, string text)
    {
        Timestamp = timestamp;
        Text = text;
    }
}
