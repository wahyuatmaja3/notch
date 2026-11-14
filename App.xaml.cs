using System;
using System.Threading;
using System.Windows;
using Notch.Services;
using Notch.Tray;
using Notch.Views;

namespace Notch;

public partial class App : System.Windows.Application
{
    private static Mutex? _singleInstanceMutex;
    private SettingsService? _settingsService;
    private LyricsCacheService? _lyricsCacheService;
    private LyricsService? _lyricsService;
    private SmtcMediaService? _smtcService;
    private WebSocketBridgeService? _wsService;
    private MediaManager? _mediaManager;
    private NotchWindow? _notchWindow;
    private SettingsWindow? _settingsWindow;
    private TrayIconManager? _trayManager;

    protected override async void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        // Ensure single instance
        const string mutexName = "Global\\NotchDynamicIsland_SingleInstance";
        _singleInstanceMutex = new Mutex(true, mutexName, out bool createdNew);
        if (!createdNew)
        {
            MessageBox.Show("Notch is already running in the system tray.", "Notch", MessageBoxButton.OK, MessageBoxImage.Information);
            Shutdown();
            return;
        }

        try
        {
            // Initialize Core Services
            _settingsService = new SettingsService();
            _lyricsCacheService = new LyricsCacheService();
            _lyricsService = new LyricsService(_lyricsCacheService);
            _smtcService = new SmtcMediaService();
            _wsService = new WebSocketBridgeService();

            _mediaManager = new MediaManager(_smtcService, _wsService, _lyricsService, _settingsService);

            // Initialize UI Windows
            _settingsWindow = new SettingsWindow(_settingsService, _lyricsCacheService);

            _notchWindow = new NotchWindow(_mediaManager, _settingsService, () =>
            {
                _settingsWindow.Show();
                _settingsWindow.Activate();
            });

            // Initialize System Tray
            _trayManager = new TrayIconManager(_mediaManager, _notchWindow, _settingsWindow);

            // Show Dynamic Island Overlay
            _notchWindow.Show();

            // Start Media Monitoring
            await _mediaManager.StartAsync();
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Failed to initialize Notch:\n{ex.Message}\n{ex.StackTrace}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            Shutdown();
        }
    }

    protected override void OnExit(ExitEventArgs e)
    {
        _trayManager?.Dispose();
        _wsService?.Stop();
        _singleInstanceMutex?.ReleaseMutex();
        _singleInstanceMutex?.Dispose();
        base.OnExit(e);
    }
}
