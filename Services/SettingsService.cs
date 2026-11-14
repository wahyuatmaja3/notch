using System;
using System.IO;
using System.Text.Json;
using Microsoft.Win32;
using Notch.Models;

namespace Notch.Services;

public class SettingsService
{
    private static readonly string AppDataFolder = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "Notch");

    private static readonly string SettingsFilePath = Path.Combine(AppDataFolder, "settings.json");

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true
    };

    public AppSettings Settings { get; set; } = new();

    public event Action<AppSettings>? SettingsChanged;

    public SettingsService()
    {
        EnsureDirectories();
        LoadSettings();
    }

    public static string GetAppDataDirectory()
    {
        EnsureDirectories();
        return AppDataFolder;
    }

    private static void EnsureDirectories()
    {
        if (!Directory.Exists(AppDataFolder))
        {
            Directory.CreateDirectory(AppDataFolder);
        }

        var cacheDir = Path.Combine(AppDataFolder, "cache");
        if (!Directory.Exists(cacheDir))
        {
            Directory.CreateDirectory(cacheDir);
        }

        var logsDir = Path.Combine(AppDataFolder, "logs");
        if (!Directory.Exists(logsDir))
        {
            Directory.CreateDirectory(logsDir);
        }
    }

    public void LoadSettings()
    {
        try
        {
            if (File.Exists(SettingsFilePath))
            {
                var json = File.ReadAllText(SettingsFilePath);
                var loaded = JsonSerializer.Deserialize<AppSettings>(json);
                if (loaded != null)
                {
                    Settings = loaded;
                    return;
                }
            }
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"Error loading settings: {ex.Message}");
        }

        Settings = new AppSettings();
        SaveSettings();
    }

    public void SaveSettings()
    {
        try
        {
            EnsureDirectories();
            var json = JsonSerializer.Serialize(Settings, JsonOptions);
            File.WriteAllText(SettingsFilePath, json);
            ApplyStartupSetting();
            SettingsChanged?.Invoke(Settings);
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"Error saving settings: {ex.Message}");
        }
    }

    private void ApplyStartupSetting()
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Run", true);
            if (key == null) return;

            var exePath = Environment.ProcessPath;
            if (string.IsNullOrEmpty(exePath)) return;

            if (Settings.StartWithWindows)
            {
                key.SetValue("NotchDynamicIsland", $"\"{exePath}\"");
            }
            else
            {
                key.DeleteValue("NotchDynamicIsland", false);
            }
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"Error configuring startup registry: {ex.Message}");
        }
    }
}
