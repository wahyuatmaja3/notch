using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Threading;
using Notch.Models;
using Notch.Services;

namespace Notch.Views;

public partial class NotchWindow : Window
{
    private readonly MediaManager _mediaManager;
    private readonly SettingsService _settingsService;
    private readonly Action _openSettingsAction;

    private readonly DispatcherTimer _collapseTimer;
    private readonly DispatcherTimer _waveAnimTimer;
    private bool _isExpanded = false;
    private bool _isMouseOver = false;
    private double _waveStep = 0;

    public bool IsNotchExpanded => _isExpanded;

    public NotchWindow(
        MediaManager mediaManager,
        SettingsService settingsService,
        Action openSettingsAction)
    {
        InitializeComponent();

        _mediaManager = mediaManager;
        _settingsService = settingsService;
        _openSettingsAction = openSettingsAction;

        // Auto collapse timer
        _collapseTimer = new DispatcherTimer();
        _collapseTimer.Tick += (s, e) =>
        {
            _collapseTimer.Stop();
            if (!_isMouseOver && _isExpanded)
            {
                Collapse();
            }
        };

        // Equalizer wave bar animation timer
        _waveAnimTimer = new DispatcherTimer
        {
            Interval = TimeSpan.FromMilliseconds(80)
        };
        _waveAnimTimer.Tick += OnWaveTimerTick;
        _waveAnimTimer.Start();

        // Subscribe to media events
        _mediaManager.TrackChanged += OnTrackChanged;
        _mediaManager.PositionTicked += OnPositionTicked;
        _mediaManager.LyricsLoaded += OnLyricsLoaded;
        _mediaManager.LyricIndexChanged += OnLyricIndexChanged;

        _settingsService.SettingsChanged += OnSettingsChanged;

        // Set initial accent color
        ApplyAccentColor(Color.FromRgb(30, 215, 96));
    }

    private void Window_Loaded(object sender, RoutedEventArgs e)
    {
        ApplyPositionAndSettings();
    }

    public void ApplyPositionAndSettings()
    {
        var settings = _settingsService.Settings;

        // Position window top-center of primary screen
        double screenWidth = SystemParameters.PrimaryScreenWidth;
        double currentWidth = _isExpanded ? settings.ExpandedWidth : settings.CollapsedWidth;
        double currentHeight = _isExpanded ? settings.ExpandedHeight : settings.CollapsedHeight;

        double left = settings.HorizontalAlignment switch
        {
            "Left" => 40 + settings.HorizontalOffset,
            "Right" => screenWidth - currentWidth - 40 + settings.HorizontalOffset,
            _ => (screenWidth - currentWidth) / 2.0 + settings.HorizontalOffset
        };

        Left = Math.Max(0, left);
        Top = settings.VerticalOffset;
        Width = currentWidth;
        Height = currentHeight;

        // Appearance
        IslandShadowContainer.CornerRadius = new CornerRadius(settings.CornerRadius);
        IslandBorder.CornerRadius = new CornerRadius(settings.CornerRadius);
        GlassBackdrop.Opacity = settings.Opacity;

        // Visibility
        AlbumArtBorder.Visibility = settings.ShowAlbumArt ? Visibility.Visible : Visibility.Collapsed;
        AlbumArtPlaceholder.Visibility = settings.ShowAlbumArt && _mediaManager.CurrentTrack.AlbumArt == null ? Visibility.Visible : Visibility.Collapsed;
        TrackProgressBar.Visibility = settings.ShowProgressBar ? Visibility.Visible : Visibility.Collapsed;
        LyricsPanel.Visibility = settings.ShowLyrics ? Visibility.Visible : Visibility.Collapsed;
        PrevBtn.Visibility = settings.ShowControls ? Visibility.Visible : Visibility.Collapsed;
        NextBtn.Visibility = settings.ShowControls ? Visibility.Visible : Visibility.Collapsed;

        // Lyrics font size
        LyricActiveText.FontSize = settings.LyricsFontSize;
        LyricPrevText.FontSize = Math.Max(9, settings.LyricsFontSize - 3);
        LyricNextText.FontSize = Math.Max(9, settings.LyricsFontSize - 3);

        LyricPrevText.Visibility = settings.VisibleLyricLines > 1 ? Visibility.Visible : Visibility.Collapsed;
        LyricNextText.Visibility = settings.VisibleLyricLines > 2 ? Visibility.Visible : Visibility.Collapsed;

        // Collapse delay
        _collapseTimer.Interval = TimeSpan.FromSeconds(Math.Max(2, settings.CollapseDelaySeconds));
    }

    private void OnSettingsChanged(AppSettings settings)
    {
        Dispatcher.Invoke(ApplyPositionAndSettings);
    }

    private void ApplyAccentColor(Color color)
    {
        Resources["DynamicAccentColor"] = color;
        Resources["DynamicAccentBrush"] = new SolidColorBrush(color);
    }

    private void OnTrackChanged(MediaTrack track)
    {
        Dispatcher.Invoke(() =>
        {
            ApplyAccentColor(track.AccentColor);

            // Collapsed view text
            CollapsedTitleText.Text = track.HasTrack
                ? $"{track.Title} • {track.Artist}"
                : "Notch Dynamic Island";

            // Expanded view track info
            TrackTitleText.Text = track.Title;
            TrackArtistText.Text = string.IsNullOrEmpty(track.Album)
                ? track.Artist
                : $"{track.Artist} — {track.Album}";

            // Source badge
            SourceBadgeText.Text = !string.IsNullOrWhiteSpace(track.Source) ? track.Source : "Music";
            CollapsedSourceIcon.Text = track.Source.ToLowerInvariant() switch
            {
                var s when s.Contains("spotify") => "🟢",
                var s when s.Contains("youtube") => "▶",
                var s when s.Contains("chrome") => "🌐",
                var s when s.Contains("firefox") => "🦊",
                var s when s.Contains("brave") => "🦁",
                _ => "🎵"
            };

            // Album Art
            if (track.AlbumArt != null)
            {
                AlbumArtImage.Source = track.AlbumArt;
                CollapsedArtImage.Source = track.AlbumArt;
                AlbumArtBorder.Visibility = _settingsService.Settings.ShowAlbumArt ? Visibility.Visible : Visibility.Collapsed;
                AlbumArtPlaceholder.Visibility = Visibility.Collapsed;
                CollapsedArtBorder.Visibility = Visibility.Visible;
                WaveformBars.Visibility = Visibility.Collapsed;
            }
            else
            {
                AlbumArtImage.Source = null;
                CollapsedArtImage.Source = null;
                AlbumArtBorder.Visibility = Visibility.Collapsed;
                AlbumArtPlaceholder.Visibility = _settingsService.Settings.ShowAlbumArt ? Visibility.Visible : Visibility.Collapsed;
                CollapsedArtBorder.Visibility = Visibility.Collapsed;
                WaveformBars.Visibility = Visibility.Visible;
            }

            // Controls & Icons
            PlayPauseIconText.Text = track.IsPlaying ? "⏸" : "▶";

            // Reset lyrics view for new track
            LyricActiveText.Text = track.HasTrack ? "Searching lyrics..." : "Not playing";
            LyricPrevText.Text = string.Empty;
            LyricNextText.Text = string.Empty;

            // Auto-expand on new track if enabled
            if (_settingsService.Settings.AutoExpandOnNewSong && track.HasTrack)
            {
                Expand();
                RestartCollapseTimer();
            }
        });
    }

    private void OnPositionTicked(TimeSpan position)
    {
        Dispatcher.Invoke(() =>
        {
            var track = _mediaManager.CurrentTrack;
            if (track.Duration > TimeSpan.Zero)
            {
                TrackProgressBar.Value = track.ProgressPercentage;
                TimeElapsedText.Text = $"{(int)position.TotalMinutes}:{position.Seconds:D2}";
                TimeTotalText.Text = $"{(int)track.Duration.TotalMinutes}:{track.Duration.Seconds:D2}";
            }
            else
            {
                TrackProgressBar.Value = 0;
                TimeElapsedText.Text = $"{(int)position.TotalMinutes}:{position.Seconds:D2}";
                TimeTotalText.Text = "--:--";
            }

            PlayPauseIconText.Text = track.IsPlaying ? "⏸" : "▶";
        });
    }

    private void OnLyricsLoaded(List<LyricLine> lyrics)
    {
        Dispatcher.Invoke(() =>
        {
            if (lyrics == null || lyrics.Count == 0)
            {
                LyricActiveText.Text = _mediaManager.CurrentTrack.HasTrack
                    ? "No synced lyrics found"
                    : "Not playing";
                LyricPrevText.Text = string.Empty;
                LyricNextText.Text = string.Empty;
            }
        });
    }

    private void OnLyricIndexChanged(int activeIndex)
    {
        Dispatcher.Invoke(() =>
        {
            var lyrics = _mediaManager.CurrentLyrics;
            if (lyrics == null || lyrics.Count == 0) return;

            if (activeIndex >= 0 && activeIndex < lyrics.Count)
            {
                LyricActiveText.Text = lyrics[activeIndex].Text;

                LyricPrevText.Text = (activeIndex > 0)
                    ? lyrics[activeIndex - 1].Text
                    : string.Empty;

                LyricNextText.Text = (activeIndex + 1 < lyrics.Count)
                    ? lyrics[activeIndex + 1].Text
                    : string.Empty;
            }
        });
    }

    private void OnWaveTimerTick(object? sender, EventArgs e)
    {
        if (_mediaManager.CurrentTrack.IsPlaying)
        {
            _waveStep += 0.35;
            WaveBar1.Height = 4 + Math.Abs(Math.Sin(_waveStep)) * 12;
            WaveBar2.Height = 4 + Math.Abs(Math.Sin(_waveStep + 0.8)) * 14;
            WaveBar3.Height = 4 + Math.Abs(Math.Sin(_waveStep + 1.6)) * 11;
            WaveBar4.Height = 4 + Math.Abs(Math.Sin(_waveStep + 2.4)) * 9;
        }
        else
        {
            WaveBar1.Height = 4;
            WaveBar2.Height = 4;
            WaveBar3.Height = 4;
            WaveBar4.Height = 4;
        }
    }

    public void Expand()
    {
        if (_isExpanded) return;
        _isExpanded = true;

        var settings = _settingsService.Settings;
        double targetWidth = settings.ExpandedWidth;
        double targetHeight = settings.ExpandedHeight;
        double screenWidth = SystemParameters.PrimaryScreenWidth;
        double targetLeft = (screenWidth - targetWidth) / 2.0 + settings.HorizontalOffset;

        AnimateIsland(targetLeft, targetWidth, targetHeight, true);
    }

    public void Collapse()
    {
        if (!_isExpanded) return;
        _isExpanded = false;

        var settings = _settingsService.Settings;
        double targetWidth = settings.CollapsedWidth;
        double targetHeight = settings.CollapsedHeight;
        double screenWidth = SystemParameters.PrimaryScreenWidth;
        double targetLeft = (screenWidth - targetWidth) / 2.0 + settings.HorizontalOffset;

        AnimateIsland(targetLeft, targetWidth, targetHeight, false);
    }

    public void ToggleExpand()
    {
        if (_isExpanded)
        {
            Collapse();
        }
        else
        {
            Expand();
        }
    }

    private void AnimateIsland(double targetLeft, double targetWidth, double targetHeight, bool expanding)
    {
        var duration = TimeSpan.FromMilliseconds(260);
        var ease = new CubicEase { EasingMode = EasingMode.EaseOut };

        // Width animation
        var animWidth = new DoubleAnimation(targetWidth, duration) { EasingFunction = ease };
        // Height animation
        var animHeight = new DoubleAnimation(targetHeight, duration) { EasingFunction = ease };
        // Left position animation (to keep centered)
        var animLeft = new DoubleAnimation(Math.Max(0, targetLeft), duration) { EasingFunction = ease };

        if (expanding)
        {
            // Switch views
            CollapsedView.Visibility = Visibility.Collapsed;
            ExpandedView.Visibility = Visibility.Visible;
            var fadeIn = new DoubleAnimation(0.0, 1.0, TimeSpan.FromMilliseconds(200));
            ExpandedView.BeginAnimation(OpacityProperty, fadeIn);
        }
        else
        {
            ExpandedView.Visibility = Visibility.Collapsed;
            CollapsedView.Visibility = Visibility.Visible;
            var fadeIn = new DoubleAnimation(0.0, 1.0, TimeSpan.FromMilliseconds(200));
            CollapsedView.BeginAnimation(OpacityProperty, fadeIn);
        }

        BeginAnimation(WidthProperty, animWidth);
        BeginAnimation(HeightProperty, animHeight);
        BeginAnimation(LeftProperty, animLeft);
    }

    private void RestartCollapseTimer()
    {
        _collapseTimer.Stop();
        _collapseTimer.Start();
    }

    private void Window_MouseEnter(object sender, MouseEventArgs e)
    {
        _isMouseOver = true;
        _collapseTimer.Stop();
        if (!_isExpanded)
        {
            Expand();
        }
    }

    private void Window_MouseLeave(object sender, MouseEventArgs e)
    {
        _isMouseOver = false;
        RestartCollapseTimer();
    }

    private void Window_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ClickCount == 2)
        {
            ToggleExpand();
            return;
        }

        if (e.ButtonState == MouseButtonState.Pressed)
        {
            try
            {
                DragMove();
            }
            catch { }
        }
    }

    private async void PlayPauseBtn_Click(object sender, RoutedEventArgs e)
    {
        await _mediaManager.TogglePlayPauseAsync();
        RestartCollapseTimer();
    }

    private async void NextBtn_Click(object sender, RoutedEventArgs e)
    {
        await _mediaManager.SkipNextAsync();
        RestartCollapseTimer();
    }

    private async void PrevBtn_Click(object sender, RoutedEventArgs e)
    {
        await _mediaManager.SkipPreviousAsync();
        RestartCollapseTimer();
    }

    private void CollapseBtn_Click(object sender, RoutedEventArgs e)
    {
        Collapse();
    }

    private void QuickSettingsBtn_Click(object sender, RoutedEventArgs e)
    {
        _openSettingsAction();
    }
}
