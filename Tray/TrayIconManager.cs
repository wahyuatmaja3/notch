using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using Hardcodet.Wpf.TaskbarNotification;
using Notch.Models;
using Notch.Services;
using Notch.Views;

namespace Notch.Tray;

public class TrayIconManager : IDisposable
{
    private readonly TaskbarIcon _notifyIcon;
    private readonly MediaManager _mediaManager;
    private readonly NotchWindow _notchWindow;
    private readonly SettingsWindow _settingsWindow;
    private MenuItem? _songHeaderItem;
    private MenuItem? _playPauseItem;

    public TrayIconManager(
        MediaManager mediaManager,
        NotchWindow notchWindow,
        SettingsWindow settingsWindow)
    {
        _mediaManager = mediaManager;
        _notchWindow = notchWindow;
        _settingsWindow = settingsWindow;

        _notifyIcon = new TaskbarIcon
        {
            ToolTipText = "Notch Dynamic Island",
            Icon = CreateProceduralIcon()
        };

        _notifyIcon.TrayLeftMouseDown += (s, e) =>
        {
            if (_notchWindow.Visibility == Visibility.Visible)
            {
                _notchWindow.ToggleExpand();
            }
            else
            {
                _notchWindow.Show();
                _notchWindow.Expand();
            }
        };

        BuildContextMenu();

        _mediaManager.TrackChanged += OnTrackChanged;
    }

    private static Icon CreateProceduralIcon()
    {
        // Generate a 32x32 sleek Dynamic Island pill icon programmatically
        using var bmp = new Bitmap(32, 32);
        using (var g = Graphics.FromImage(bmp))
        {
            g.SmoothingMode = SmoothingMode.AntiAlias;
            g.Clear(System.Drawing.Color.Transparent);

            // Draw rounded notch pill
            using var brush = new SolidBrush(System.Drawing.Color.FromArgb(240, 18, 18, 24));
            using var pen = new System.Drawing.Pen(System.Drawing.Color.FromArgb(200, 59, 130, 246), 1.5f);

            var rect = new Rectangle(2, 8, 28, 16);
            using var path = GetRoundedRect(rect, 8);
            g.FillPath(brush, path);
            g.DrawPath(pen, path);

            // Draw mini play indicator
            using var accentBrush = new SolidBrush(System.Drawing.Color.FromArgb(255, 30, 215, 96));
            g.FillEllipse(accentBrush, 7, 13, 5, 5);

            // Mini waveform bars
            using var barBrush = new SolidBrush(System.Drawing.Color.FromArgb(230, 255, 255, 255));
            g.FillRectangle(barBrush, 16, 14, 2, 5);
            g.FillRectangle(barBrush, 20, 11, 2, 8);
            g.FillRectangle(barBrush, 24, 13, 2, 6);
        }

        var hIcon = bmp.GetHicon();
        return Icon.FromHandle(hIcon);
    }

    private static GraphicsPath GetRoundedRect(Rectangle bounds, int radius)
    {
        int diameter = radius * 2;
        var size = new System.Drawing.Size(diameter, diameter);
        var arc = new Rectangle(bounds.Location, size);
        var path = new GraphicsPath();

        path.AddArc(arc, 180, 90);
        arc.X = bounds.Right - diameter;
        path.AddArc(arc, 270, 90);
        arc.Y = bounds.Bottom - diameter;
        path.AddArc(arc, 0, 90);
        arc.X = bounds.Left;
        path.AddArc(arc, 90, 90);
        path.CloseFigure();
        return path;
    }

    private void BuildContextMenu()
    {
        var menu = new ContextMenu
        {
            Background = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(28, 28, 35)),
            Foreground = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(240, 240, 240)),
            BorderThickness = new Thickness(1),
            BorderBrush = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(50, 50, 65))
        };

        // Header Song Info
        _songHeaderItem = new MenuItem
        {
            Header = "🎵 No track playing",
            IsEnabled = false,
            FontWeight = FontWeights.SemiBold
        };
        menu.Items.Add(_songHeaderItem);

        menu.Items.Add(new Separator());

        // Play / Pause
        _playPauseItem = new MenuItem { Header = "⏯ Play / Pause" };
        _playPauseItem.Click += async (s, e) => await _mediaManager.TogglePlayPauseAsync();
        menu.Items.Add(_playPauseItem);

        // Next
        var nextItem = new MenuItem { Header = "⏭ Next Track" };
        nextItem.Click += async (s, e) => await _mediaManager.SkipNextAsync();
        menu.Items.Add(nextItem);

        // Previous
        var prevItem = new MenuItem { Header = "⏮ Previous Track" };
        prevItem.Click += async (s, e) => await _mediaManager.SkipPreviousAsync();
        menu.Items.Add(prevItem);

        menu.Items.Add(new Separator());

        // Toggle Show/Hide
        var toggleShowItem = new MenuItem { Header = "👁 Toggle Notch Overlay" };
        toggleShowItem.Click += (s, e) =>
        {
            if (_notchWindow.Visibility == Visibility.Visible)
            {
                _notchWindow.Hide();
            }
            else
            {
                _notchWindow.Show();
                _notchWindow.Expand();
            }
        };
        menu.Items.Add(toggleShowItem);

        // Settings
        var settingsItem = new MenuItem { Header = "⚙ Settings..." };
        settingsItem.Click += (s, e) =>
        {
            _settingsWindow.Show();
            _settingsWindow.Activate();
        };
        menu.Items.Add(settingsItem);

        // About
        var aboutItem = new MenuItem { Header = "ℹ About Notch" };
        aboutItem.Click += (s, e) =>
        {
            MessageBox.Show(
                "Notch — Dynamic Island for Windows\nVersion 1.0.0\n\nShows real-time synced lyrics and media from YouTube Music and Spotify.\n\nRunning standalone as portable application.",
                "About Notch",
                MessageBoxButton.OK,
                MessageBoxImage.Information);
        };
        menu.Items.Add(aboutItem);

        menu.Items.Add(new Separator());

        // Quit
        var quitItem = new MenuItem { Header = "❌ Exit Notch" };
        quitItem.Click += (s, e) =>
        {
            _notifyIcon.Dispose();
            System.Windows.Application.Current.Shutdown();
        };
        menu.Items.Add(quitItem);

        _notifyIcon.ContextMenu = menu;
    }

    private void OnTrackChanged(MediaTrack track)
    {
        System.Windows.Application.Current.Dispatcher.Invoke(() =>
        {
            if (track.HasTrack)
            {
                _notifyIcon.ToolTipText = $"Notch — {track.Title} by {track.Artist}";
                if (_songHeaderItem != null)
                {
                    _songHeaderItem.Header = $"🎵 {track.Title} • {track.Artist}";
                }
            }
            else
            {
                _notifyIcon.ToolTipText = "Notch Dynamic Island";
                if (_songHeaderItem != null)
                {
                    _songHeaderItem.Header = "🎵 No track playing";
                }
            }
        });
    }

    public void Dispose()
    {
        _notifyIcon.Dispose();
    }
}
