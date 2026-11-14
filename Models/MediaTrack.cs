using System;
using System.Windows.Media;

namespace Notch.Models;

public class MediaTrack
{
    public string Title { get; set; } = "No Track Playing";
    public string Artist { get; set; } = "Waiting for music...";
    public string Album { get; set; } = string.Empty;
    public ImageSource? AlbumArt { get; set; }
    public TimeSpan Duration { get; set; } = TimeSpan.Zero;
    public TimeSpan Position { get; set; } = TimeSpan.Zero;
    public bool IsPlaying { get; set; } = false;
    public string Source { get; set; } = "Media";
    public string TrackId { get; set; } = string.Empty;
    public Color AccentColor { get; set; } = Color.FromRgb(30, 215, 96); // Default Spotify Green / Cyber Green
    public bool CanPlayPause { get; set; } = true;
    public bool CanSkipNext { get; set; } = true;
    public bool CanSkipPrevious { get; set; } = true;

    public string FormattedPosition => Duration > TimeSpan.Zero
        ? $"{(int)Position.TotalMinutes}:{Position.Seconds:D2} / {(int)Duration.TotalMinutes}:{Duration.Seconds:D2}"
        : $"{(int)Position.TotalMinutes}:{Position.Seconds:D2}";

    public double ProgressPercentage => Duration.TotalMilliseconds > 0
        ? Math.Clamp(Position.TotalMilliseconds / Duration.TotalMilliseconds * 100.0, 0, 100)
        : 0;

    public bool HasTrack => !string.IsNullOrWhiteSpace(Title) && Title != "No Track Playing";
}
