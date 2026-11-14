using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using System.Windows.Media;
using System.Windows.Threading;
using Notch.Models;

namespace Notch.Services;

public class MediaManager
{
    private readonly SmtcMediaService _smtcService;
    private readonly WebSocketBridgeService _wsService;
    private readonly LyricsService _lyricsService;
    private readonly SettingsService _settingsService;
    private readonly DispatcherTimer _tickerTimer;

    private MediaTrack _currentTrack = new();
    private List<LyricLine> _currentLyrics = new();
    private int _currentLyricIndex = -1;
    private bool _isUsingExtension = false;
    private DateTime _lastExtUpdateTime = DateTime.MinValue;

    public event Action<MediaTrack>? TrackChanged;
    public event Action<TimeSpan>? PositionTicked;
    public event Action<List<LyricLine>>? LyricsLoaded;
    public event Action<int>? LyricIndexChanged;

    public MediaTrack CurrentTrack => _currentTrack;
    public List<LyricLine> CurrentLyrics => _currentLyrics;
    public int CurrentLyricIndex => _currentLyricIndex;

    public MediaManager(
        SmtcMediaService smtcService,
        WebSocketBridgeService wsService,
        LyricsService lyricsService,
        SettingsService settingsService)
    {
        _smtcService = smtcService;
        _wsService = wsService;
        _lyricsService = lyricsService;
        _settingsService = settingsService;

        _smtcService.TrackUpdated += OnSmtcTrackUpdated;
        _smtcService.PositionUpdated += OnSmtcPositionUpdated;
        _smtcService.PlaybackStateChanged += OnSmtcPlaybackStateChanged;

        _wsService.ExtensionTrackReceived += OnExtensionTrackReceived;
        _wsService.ExtensionPositionReceived += OnExtensionPositionReceived;

        // Position ticking timer for silky-smooth progress & lyrics sync
        _tickerTimer = new DispatcherTimer
        {
            Interval = TimeSpan.FromMilliseconds(250)
        };
        _tickerTimer.Tick += OnTickerTick;
        _tickerTimer.Start();
    }

    public async Task StartAsync()
    {
        if (_settingsService.Settings.EnableSmtc)
        {
            await _smtcService.InitializeAsync();
        }

        if (_settingsService.Settings.EnableWebSocketBridge)
        {
            _wsService.Start(_settingsService.Settings.WebSocketPort);
        }
    }

    private void OnTickerTick(object? sender, EventArgs e)
    {
        if (_currentTrack.IsPlaying && _currentTrack.Duration > TimeSpan.Zero)
        {
            // Advance position by ticker interval
            var newPos = _currentTrack.Position + _tickerTimer.Interval;
            if (newPos <= _currentTrack.Duration)
            {
                _currentTrack.Position = newPos;
            }

            PositionTicked?.Invoke(_currentTrack.Position);
            UpdateActiveLyric();
        }
    }

    private void OnSmtcTrackUpdated(MediaTrack track)
    {
        // If extension recently provided data (< 4s), prefer extension
        if (_isUsingExtension && (DateTime.UtcNow - _lastExtUpdateTime).TotalSeconds < 4.0)
        {
            return;
        }

        _isUsingExtension = false;
        ProcessTrackUpdate(track);
    }

    private void OnSmtcPositionUpdated(TimeSpan position)
    {
        if (_isUsingExtension) return;
        _currentTrack.Position = position;
        PositionTicked?.Invoke(position);
        UpdateActiveLyric();
    }

    private void OnSmtcPlaybackStateChanged(bool isPlaying)
    {
        if (_isUsingExtension) return;
        _currentTrack.IsPlaying = isPlaying;
    }

    private void OnExtensionTrackReceived(MediaTrack track)
    {
        _isUsingExtension = true;
        _lastExtUpdateTime = DateTime.UtcNow;
        ProcessTrackUpdate(track);
    }

    private void OnExtensionPositionReceived(TimeSpan position)
    {
        _isUsingExtension = true;
        _lastExtUpdateTime = DateTime.UtcNow;
        _currentTrack.Position = position;
        PositionTicked?.Invoke(position);
        UpdateActiveLyric();
    }

    private void ProcessTrackUpdate(MediaTrack track)
    {
        bool trackChanged = track.Title != _currentTrack.Title || track.Artist != _currentTrack.Artist;

        // Accent color computation
        if (_settingsService.Settings.AutoAccentColor)
        {
            var defaultColor = Color.FromRgb(30, 215, 96);
            track.AccentColor = ColorExtractor.ExtractDominantColor(track.AlbumArt, defaultColor);
        }
        else
        {
            try
            {
                track.AccentColor = (Color)ColorConverter.ConvertFromString(_settingsService.Settings.CustomAccentColorHex);
            }
            catch
            {
                track.AccentColor = Color.FromRgb(59, 130, 246);
            }
        }

        _currentTrack = track;
        TrackChanged?.Invoke(_currentTrack);

        if (trackChanged)
        {
            _ = LoadLyricsForCurrentTrackAsync();
        }
    }

    private async Task LoadLyricsForCurrentTrackAsync()
    {
        if (!_currentTrack.HasTrack)
        {
            _currentLyrics.Clear();
            _currentLyricIndex = -1;
            LyricsLoaded?.Invoke(_currentLyrics);
            LyricIndexChanged?.Invoke(_currentLyricIndex);
            return;
        }

        string title = _currentTrack.Title;
        string artist = _currentTrack.Artist;
        double durationSec = _currentTrack.Duration.TotalSeconds;

        var lyrics = await _lyricsService.GetLyricsAsync(title, artist, durationSec);

        // Verify track hasn't changed during fetch
        if (_currentTrack.Title == title && _currentTrack.Artist == artist)
        {
            _currentLyrics = lyrics;
            _currentLyricIndex = -1;
            LyricsLoaded?.Invoke(_currentLyrics);
            UpdateActiveLyric();
        }
    }

    private void UpdateActiveLyric()
    {
        if (_currentLyrics.Count == 0) return;

        int newIndex = _lyricsService.GetActiveIndex(
            _currentLyrics,
            _currentTrack.Position,
            _settingsService.Settings.SyncOffsetMs);

        if (newIndex != _currentLyricIndex)
        {
            _currentLyricIndex = newIndex;
            LyricIndexChanged?.Invoke(_currentLyricIndex);
        }
    }

    // Media Controls
    public async Task TogglePlayPauseAsync()
    {
        if (_isUsingExtension)
        {
            await _wsService.SendCommandAsync("playpause");
            _currentTrack.IsPlaying = !_currentTrack.IsPlaying;
        }
        else
        {
            await _smtcService.TogglePlayPauseAsync();
        }
    }

    public async Task SkipNextAsync()
    {
        if (_isUsingExtension)
        {
            await _wsService.SendCommandAsync("next");
        }
        else
        {
            await _smtcService.SkipNextAsync();
        }
    }

    public async Task SkipPreviousAsync()
    {
        if (_isUsingExtension)
        {
            await _wsService.SendCommandAsync("previous");
        }
        else
        {
            await _smtcService.SkipPreviousAsync();
        }
    }
}
