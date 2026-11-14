using System.Text.Json.Serialization;

namespace Notch.Models;

public class ExtensionMessage
{
    [JsonPropertyName("type")]
    public string Type { get; set; } = "track_update";

    [JsonPropertyName("source")]
    public string Source { get; set; } = "browser";

    [JsonPropertyName("title")]
    public string Title { get; set; } = string.Empty;

    [JsonPropertyName("artist")]
    public string Artist { get; set; } = string.Empty;

    [JsonPropertyName("album")]
    public string Album { get; set; } = string.Empty;

    [JsonPropertyName("duration")]
    public double DurationSeconds { get; set; } = 0;

    [JsonPropertyName("position")]
    public double PositionSeconds { get; set; } = 0;

    [JsonPropertyName("isPlaying")]
    public bool IsPlaying { get; set; } = false;

    [JsonPropertyName("trackId")]
    public string TrackId { get; set; } = string.Empty;

    [JsonPropertyName("artUrl")]
    public string ArtUrl { get; set; } = string.Empty;
}
