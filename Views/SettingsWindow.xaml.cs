using System;
using System.ComponentModel;
using System.Windows;
using System.Windows.Controls;
using Notch.Models;
using Notch.Services;

namespace Notch.Views;

public partial class SettingsWindow : Window
{
    private readonly SettingsService _settingsService;
    private readonly LyricsCacheService _lyricsCacheService;

    public SettingsWindow(SettingsService settingsService, LyricsCacheService lyricsCacheService)
    {
        InitializeComponent();
        _settingsService = settingsService;
        _lyricsCacheService = lyricsCacheService;

        LoadCurrentSettings();
    }

    private void LoadCurrentSettings()
    {
        var s = _settingsService.Settings;

        ThemeCombo.SelectedIndex = s.Theme == "Light" ? 1 : 0;
        OpacitySlider.Value = s.Opacity;
        OpacityValText.Text = $"{(int)(s.Opacity * 100)}%";

        CornerRadiusSlider.Value = s.CornerRadius;
        CornerRadiusValText.Text = $"{(int)s.CornerRadius}px";

        AutoAccentCheck.IsChecked = s.AutoAccentColor;
        ShowAlbumArtCheck.IsChecked = s.ShowAlbumArt;
        ShowProgressBarCheck.IsChecked = s.ShowProgressBar;
        ShowLyricsCheck.IsChecked = s.ShowLyrics;
        ShowControlsCheck.IsChecked = s.ShowControls;

        AlignmentCombo.SelectedIndex = s.HorizontalAlignment switch
        {
            "Left" => 1,
            "Right" => 2,
            _ => 0
        };

        VerticalOffsetSlider.Value = s.VerticalOffset;
        VerticalOffsetValText.Text = $"{(int)s.VerticalOffset}px";

        ExpandedWidthSlider.Value = s.ExpandedWidth;
        ExpandedWidthValText.Text = $"{(int)s.ExpandedWidth}px";

        AutoExpandCheck.IsChecked = s.AutoExpandOnNewSong;
        CollapseDelaySlider.Value = s.CollapseDelaySeconds;
        CollapseDelayValText.Text = $"{(int)s.CollapseDelaySeconds}s";

        StartWithWindowsCheck.IsChecked = s.StartWithWindows;
        MinimizeToTrayCheck.IsChecked = s.MinimizeToTray;

        LyricsFontSizeSlider.Value = s.LyricsFontSize;
        LyricsFontSizeValText.Text = $"{(int)s.LyricsFontSize}px";

        VisibleLinesCombo.SelectedIndex = s.VisibleLyricLines <= 1 ? 0 : 1;

        SyncOffsetSlider.Value = s.SyncOffsetMs;
        SyncOffsetValText.Text = $"{s.SyncOffsetMs} ms";

        EnableSmtcCheck.IsChecked = s.EnableSmtc;
        WsPortBox.Text = s.WebSocketPort.ToString();
    }

    private void OpacitySlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        if (OpacityValText != null)
            OpacityValText.Text = $"{(int)(e.NewValue * 100)}%";
    }

    private void CornerRadiusSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        if (CornerRadiusValText != null)
            CornerRadiusValText.Text = $"{(int)e.NewValue}px";
    }

    private void VerticalOffsetSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        if (VerticalOffsetValText != null)
            VerticalOffsetValText.Text = $"{(int)e.NewValue}px";
    }

    private void ExpandedWidthSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        if (ExpandedWidthValText != null)
            ExpandedWidthValText.Text = $"{(int)e.NewValue}px";
    }

    private void CollapseDelaySlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        if (CollapseDelayValText != null)
            CollapseDelayValText.Text = $"{(int)e.NewValue}s";
    }

    private void LyricsFontSizeSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        if (LyricsFontSizeValText != null)
            LyricsFontSizeValText.Text = $"{(int)e.NewValue}px";
    }

    private void SyncOffsetSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        if (SyncOffsetValText != null)
            SyncOffsetValText.Text = $"{(int)e.NewValue} ms";
    }

    private void SaveBtn_Click(object sender, RoutedEventArgs e)
    {
        var s = _settingsService.Settings;

        s.Theme = ThemeCombo.SelectedIndex == 1 ? "Light" : "Dark";
        s.Opacity = Math.Round(OpacitySlider.Value, 2);
        s.CornerRadius = Math.Round(CornerRadiusSlider.Value, 0);
        s.AutoAccentColor = AutoAccentCheck.IsChecked ?? true;
        s.ShowAlbumArt = ShowAlbumArtCheck.IsChecked ?? true;
        s.ShowProgressBar = ShowProgressBarCheck.IsChecked ?? true;
        s.ShowLyrics = ShowLyricsCheck.IsChecked ?? true;
        s.ShowControls = ShowControlsCheck.IsChecked ?? true;

        s.HorizontalAlignment = AlignmentCombo.SelectedIndex switch
        {
            1 => "Left",
            2 => "Right",
            _ => "Center"
        };

        s.VerticalOffset = Math.Round(VerticalOffsetSlider.Value, 0);
        s.ExpandedWidth = Math.Round(ExpandedWidthSlider.Value, 0);

        s.AutoExpandOnNewSong = AutoExpandCheck.IsChecked ?? true;
        s.CollapseDelaySeconds = Math.Round(CollapseDelaySlider.Value, 1);
        s.StartWithWindows = StartWithWindowsCheck.IsChecked ?? false;
        s.MinimizeToTray = MinimizeToTrayCheck.IsChecked ?? true;

        s.LyricsFontSize = Math.Round(LyricsFontSizeSlider.Value, 0);
        s.VisibleLyricLines = VisibleLinesCombo.SelectedIndex == 0 ? 1 : 3;
        s.SyncOffsetMs = (int)Math.Round(SyncOffsetSlider.Value);

        s.EnableSmtc = EnableSmtcCheck.IsChecked ?? true;
        if (int.TryParse(WsPortBox.Text, out int port) && port > 1024 && port < 65535)
        {
            s.WebSocketPort = port;
        }

        _settingsService.SaveSettings();
        Hide();
    }

    private void ClearCacheBtn_Click(object sender, RoutedEventArgs e)
    {
        _lyricsCacheService.ClearCache();
        MessageBox.Show(this, "Local lyrics cache cleared successfully.", "Lyrics Cache", MessageBoxButton.OK, MessageBoxImage.Information);
    }

    private void ResetDefaultsBtn_Click(object sender, RoutedEventArgs e)
    {
        if (MessageBox.Show(this, "Reset all settings to default values?", "Confirm Reset", MessageBoxButton.YesNo, MessageBoxImage.Question) == MessageBoxResult.Yes)
        {
            _settingsService.Settings = new AppSettings();
            _settingsService.SaveSettings();
            LoadCurrentSettings();
        }
    }

    private void CloseBtn_Click(object sender, RoutedEventArgs e)
    {
        Hide();
    }

    protected override void OnClosing(CancelEventArgs e)
    {
        // Hide instead of close to allow re-opening cleanly
        e.Cancel = true;
        Hide();
    }
}
