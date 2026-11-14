using System;

namespace Notch.Models;

public class AppSettings
{
    // Appearance
    public string Theme { get; set; } = "Dark";
    public double Opacity { get; set; } = 0.92;
    public double CornerRadius { get; set; } = 28;
    public bool AutoAccentColor { get; set; } = true;
    public string CustomAccentColorHex { get; set; } = "#3B82F6";
    public bool ShowAlbumArt { get; set; } = true;
    public bool ShowProgressBar { get; set; } = true;
    public bool ShowLyrics { get; set; } = true;
    public bool ShowControls { get; set; } = true;

    // Position & Size
    public string HorizontalAlignment { get; set; } = "Center";
    public double HorizontalOffset { get; set; } = 0;
    public double VerticalOffset { get; set; } = 12;
    public double CollapsedWidth { get; set; } = 230;
    public double CollapsedHeight { get; set; } = 40;
    public double ExpandedWidth { get; set; } = 440;
    public double ExpandedHeight { get; set; } = 230;

    // Behavior
    public bool AutoExpandOnNewSong { get; set; } = true;
    public double CollapseDelaySeconds { get; set; } = 5.0;
    public bool AutoHideWhenNoMusic { get; set; } = false;
    public bool ClickThroughWhenCollapsed { get; set; } = false;
    public bool StartWithWindows { get; set; } = false;
    public bool MinimizeToTray { get; set; } = true;

    // Lyrics
    public double LyricsFontSize { get; set; } = 14;
    public int VisibleLyricLines { get; set; } = 3;
    public int SyncOffsetMs { get; set; } = 0;
    public bool CacheLyrics { get; set; } = true;

    // Sources
    public int WebSocketPort { get; set; } = 7891;
    public bool EnableWebSocketBridge { get; set; } = true;
    public bool EnableSmtc { get; set; } = true;
}
