using System;
using System.IO;
using System.Threading.Tasks;
using System.Windows.Media.Imaging;
using Windows.Media.Control;
using Windows.Storage.Streams;
using Notch.Models;

namespace Notch.Services;

public class SmtcMediaService
{
    private GlobalSystemMediaTransportControlsSessionManager? _sessionManager;
    private GlobalSystemMediaTransportControlsSession? _currentSession;

    public event Action<MediaTrack>? TrackUpdated;
    public event Action<TimeSpan>? PositionUpdated;
    public event Action<bool>? PlaybackStateChanged;

    public bool IsAvailable => _sessionManager != null;
    public MediaTrack CurrentTrack { get; private set; } = new();

    public async Task InitializeAsync()
    {
        try
        {
            _sessionManager = await GlobalSystemMediaTransportControlsSessionManager.RequestAsync();
            if (_sessionManager != null)
            {
                _sessionManager.CurrentSessionChanged += OnCurrentSessionChanged;
                _sessionManager.SessionsChanged += OnSessionsChanged;

                UpdateCurrentSession(_sessionManager.GetCurrentSession());
            }
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"Failed to init SMTC session manager: {ex.Message}");
        }
    }

    private void OnSessionsChanged(GlobalSystemMediaTransportControlsSessionManager sender, SessionsChangedEventArgs args)
    {
        UpdateCurrentSession(sender.GetCurrentSession());
    }

    private void OnCurrentSessionChanged(GlobalSystemMediaTransportControlsSessionManager sender, CurrentSessionChangedEventArgs args)
    {
        UpdateCurrentSession(sender.GetCurrentSession());
    }

    private void UpdateCurrentSession(GlobalSystemMediaTransportControlsSession? session)
    {
        if (_currentSession != null)
        {
            _currentSession.MediaPropertiesChanged -= OnMediaPropertiesChanged;
            _currentSession.TimelinePropertiesChanged -= OnTimelinePropertiesChanged;
            _currentSession.PlaybackInfoChanged -= OnPlaybackInfoChanged;
        }

        _currentSession = session;

        if (_currentSession != null)
        {
            _currentSession.MediaPropertiesChanged += OnMediaPropertiesChanged;
            _currentSession.TimelinePropertiesChanged += OnTimelinePropertiesChanged;
            _currentSession.PlaybackInfoChanged += OnPlaybackInfoChanged;

            _ = RefreshSessionDataAsync();
        }
        else
        {
            CurrentTrack = new MediaTrack
            {
                Title = "No Track Playing",
                Artist = "Waiting for music...",
                IsPlaying = false
            };
            TrackUpdated?.Invoke(CurrentTrack);
        }
    }

    private void OnMediaPropertiesChanged(GlobalSystemMediaTransportControlsSession sender, MediaPropertiesChangedEventArgs args)
    {
        _ = RefreshSessionDataAsync();
    }

    private void OnTimelinePropertiesChanged(GlobalSystemMediaTransportControlsSession sender, TimelinePropertiesChangedEventArgs args)
    {
        UpdateTimeline();
    }

    private void OnPlaybackInfoChanged(GlobalSystemMediaTransportControlsSession sender, PlaybackInfoChangedEventArgs args)
    {
        UpdatePlaybackInfo();
    }

    public async Task RefreshSessionDataAsync()
    {
        if (_currentSession == null) return;

        try
        {
            var mediaProps = await _currentSession.TryGetMediaPropertiesAsync();
            if (mediaProps == null) return;

            var timeline = _currentSession.GetTimelineProperties();
            var playback = _currentSession.GetPlaybackInfo();

            var appId = _currentSession.SourceAppUserModelId ?? string.Empty;
            string source = DetectSourceName(appId);

            BitmapImage? albumArt = null;
            if (mediaProps.Thumbnail != null)
            {
                try
                {
                    using var streamRef = await mediaProps.Thumbnail.OpenReadAsync();
                    using var netStream = streamRef.AsStreamForRead();
                    using var memStream = new MemoryStream();
                    await netStream.CopyToAsync(memStream);
                    memStream.Position = 0;

                    var bmp = new BitmapImage();
                    bmp.BeginInit();
                    bmp.CacheOption = BitmapCacheOption.OnLoad;
                    bmp.StreamSource = memStream;
                    bmp.EndInit();
                    bmp.Freeze();
                    albumArt = bmp;
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"Error decoding thumbnail: {ex.Message}");
                }
            }

            bool isPlaying = playback?.PlaybackStatus == GlobalSystemMediaTransportControlsSessionPlaybackStatus.Playing;
            var controls = playback?.Controls;

            var track = new MediaTrack
            {
                Title = !string.IsNullOrWhiteSpace(mediaProps.Title) ? mediaProps.Title : "Unknown Title",
                Artist = !string.IsNullOrWhiteSpace(mediaProps.Artist) ? mediaProps.Artist : "Unknown Artist",
                Album = mediaProps.AlbumTitle ?? string.Empty,
                AlbumArt = albumArt,
                Duration = timeline.EndTime - timeline.StartTime,
                Position = timeline.Position,
                IsPlaying = isPlaying,
                Source = source,
                CanPlayPause = controls?.IsPlayPauseToggleEnabled == true || controls?.IsPlayEnabled == true || controls?.IsPauseEnabled == true,
                CanSkipNext = controls?.IsNextEnabled == true,
                CanSkipPrevious = controls?.IsPreviousEnabled == true
            };

            CurrentTrack = track;
            TrackUpdated?.Invoke(track);
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"Failed to refresh SMTC data: {ex.Message}");
        }
    }

    private void UpdateTimeline()
    {
        if (_currentSession == null) return;

        try
        {
            var timeline = _currentSession.GetTimelineProperties();
            CurrentTrack.Position = timeline.Position;
            if (timeline.EndTime > TimeSpan.Zero)
            {
                CurrentTrack.Duration = timeline.EndTime - timeline.StartTime;
            }
            PositionUpdated?.Invoke(CurrentTrack.Position);
        }
        catch { }
    }

    private void UpdatePlaybackInfo()
    {
        if (_currentSession == null) return;

        try
        {
            var playback = _currentSession.GetPlaybackInfo();
            bool isPlaying = playback?.PlaybackStatus == GlobalSystemMediaTransportControlsSessionPlaybackStatus.Playing;
            CurrentTrack.IsPlaying = isPlaying;
            PlaybackStateChanged?.Invoke(isPlaying);
        }
        catch { }
    }

    private static string DetectSourceName(string appId)
    {
        var lower = appId.ToLowerInvariant();
        if (lower.Contains("chrome")) return "Chrome";
        if (lower.Contains("brave")) return "Brave";
        if (lower.Contains("firefox")) return "Firefox";
        if (lower.Contains("spotify")) return "Spotify";
        if (lower.Contains("edge")) return "Edge";
        return "Browser";
    }

    // Controls
    public async Task<bool> TogglePlayPauseAsync()
    {
        if (_currentSession == null) return false;
        try
        {
            return await _currentSession.TryTogglePlayPauseAsync();
        }
        catch { return false; }
    }

    public async Task<bool> SkipNextAsync()
    {
        if (_currentSession == null) return false;
        try
        {
            return await _currentSession.TrySkipNextAsync();
        }
        catch { return false; }
    }

    public async Task<bool> SkipPreviousAsync()
    {
        if (_currentSession == null) return false;
        try
        {
            return await _currentSession.TrySkipPreviousAsync();
        }
        catch { return false; }
    }
}
