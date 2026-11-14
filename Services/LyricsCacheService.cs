using System;
using System.IO;
using Microsoft.Data.Sqlite;

namespace Notch.Services;

public class LyricsCacheService
{
    private readonly string _connectionString;

    public LyricsCacheService()
    {
        var appData = SettingsService.GetAppDataDirectory();
        var dbPath = Path.Combine(appData, "cache", "lyrics.db");
        _connectionString = new SqliteConnectionStringBuilder
        {
            DataSource = dbPath,
            Mode = SqliteOpenMode.ReadWriteCreate,
            Cache = SqliteCacheMode.Shared
        }.ToString();

        InitializeDatabase();
    }

    private void InitializeDatabase()
    {
        try
        {
            using var connection = new SqliteConnection(_connectionString);
            connection.Open();

            var cmd = connection.CreateCommand();
            cmd.CommandText = @"
                CREATE TABLE IF NOT EXISTS lyrics (
                    cache_key TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    lrc_text TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_lyrics_key ON lyrics(cache_key);
            ";
            cmd.ExecuteNonQuery();
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"Failed to init SQLite lyrics cache: {ex.Message}");
        }
    }

    private static string NormalizeKey(string title, string artist)
    {
        var cleanTitle = title.Trim().ToLowerInvariant();
        var cleanArtist = artist.Trim().ToLowerInvariant();
        return $"{cleanArtist}___{cleanTitle}";
    }

    public string? GetCachedLyrics(string title, string artist)
    {
        if (string.IsNullOrWhiteSpace(title)) return null;

        try
        {
            var key = NormalizeKey(title, artist);
            using var connection = new SqliteConnection(_connectionString);
            connection.Open();

            var cmd = connection.CreateCommand();
            cmd.CommandText = "SELECT lrc_text FROM lyrics WHERE cache_key = $key LIMIT 1";
            cmd.Parameters.AddWithValue("$key", key);

            var result = cmd.ExecuteScalar();
            if (result != null && result != DBNull.Value)
            {
                return (string)result;
            }
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"Error reading lyrics cache: {ex.Message}");
        }

        return null;
    }

    public void CacheLyrics(string title, string artist, string lrcText)
    {
        if (string.IsNullOrWhiteSpace(title) || string.IsNullOrWhiteSpace(lrcText)) return;

        try
        {
            var key = NormalizeKey(title, artist);
            using var connection = new SqliteConnection(_connectionString);
            connection.Open();

            var cmd = connection.CreateCommand();
            cmd.CommandText = @"
                INSERT OR REPLACE INTO lyrics (cache_key, title, artist, lrc_text, created_at)
                VALUES ($key, $title, $artist, $lrc, $created_at)
            ";
            cmd.Parameters.AddWithValue("$key", key);
            cmd.Parameters.AddWithValue("$title", title);
            cmd.Parameters.AddWithValue("$artist", artist);
            cmd.Parameters.AddWithValue("$lrc", lrcText);
            cmd.Parameters.AddWithValue("$created_at", DateTime.UtcNow.ToString("o"));

            cmd.ExecuteNonQuery();
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"Error writing lyrics cache: {ex.Message}");
        }
    }

    public void ClearCache()
    {
        try
        {
            using var connection = new SqliteConnection(_connectionString);
            connection.Open();

            var cmd = connection.CreateCommand();
            cmd.CommandText = "DELETE FROM lyrics";
            cmd.ExecuteNonQuery();
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"Error clearing lyrics cache: {ex.Message}");
        }
    }
}
