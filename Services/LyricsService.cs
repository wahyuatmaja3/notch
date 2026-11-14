using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using Notch.Models;

namespace Notch.Services;

public class LyricsService
{
    private readonly HttpClient _httpClient;
    private readonly LyricsCacheService _cacheService;
    private static readonly Regex LrcTimeRegex = new(@"\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)", RegexOptions.Compiled);
    private static readonly Regex CleanTitleRegex = new(@"\s*(\(|\[)(official|video|audio|lyrics|hd|4k|remastered|feat\.|ft\.).*?(\)|\])", RegexOptions.IgnoreCase | RegexOptions.Compiled);

    public LyricsService(LyricsCacheService cacheService)
    {
        _cacheService = cacheService;
        _httpClient = new HttpClient
        {
            Timeout = TimeSpan.FromSeconds(10)
        };
        _httpClient.DefaultRequestHeaders.Add("User-Agent", "NotchDynamicIsland/1.0.0 (https://github.com/notch)");
    }

    public async Task<List<LyricLine>> GetLyricsAsync(string rawTitle, string rawArtist, double durationSeconds)
    {
        if (string.IsNullOrWhiteSpace(rawTitle))
        {
            return new List<LyricLine>();
        }

        var cleanTitle = CleanTrackTitle(rawTitle);
        var cleanArtist = CleanArtistName(rawArtist);

        // 1. Check local SQLite cache
        var cachedLrc = _cacheService.GetCachedLyrics(cleanTitle, cleanArtist);
        if (!string.IsNullOrEmpty(cachedLrc))
        {
            return ParseLrc(cachedLrc);
        }

        // 2. Query LRCLIB API
        try
        {
            string? lrcContent = await FetchFromLrcLibAsync(cleanTitle, cleanArtist, (int)Math.Round(durationSeconds));
            if (!string.IsNullOrEmpty(lrcContent))
            {
                _cacheService.CacheLyrics(cleanTitle, cleanArtist, lrcContent);
                return ParseLrc(lrcContent);
            }
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"Failed to fetch from LRCLIB: {ex.Message}");
        }

        return new List<LyricLine>();
    }

    private async Task<string?> FetchFromLrcLibAsync(string title, string artist, int durationSeconds)
    {
        try
        {
            // Exact GET query
            string url = $"https://lrclib.net/api/get?track_name={Uri.EscapeDataString(title)}&artist_name={Uri.EscapeDataString(artist)}";
            if (durationSeconds > 0)
            {
                url += $"&duration={durationSeconds}";
            }

            var response = await _httpClient.GetAsync(url);
            if (response.IsSuccessStatusCode)
            {
                var json = await response.Content.ReadAsStringAsync();
                using var doc = JsonDocument.Parse(json);
                var root = doc.RootElement;

                if (root.TryGetProperty("syncedLyrics", out var syncedProp) && syncedProp.ValueKind == JsonValueKind.String)
                {
                    var synced = syncedProp.GetString();
                    if (!string.IsNullOrWhiteSpace(synced)) return synced;
                }

                if (root.TryGetProperty("plainLyrics", out var plainProp) && plainProp.ValueKind == JsonValueKind.String)
                {
                    return plainProp.GetString();
                }
            }

            // Search fallback
            string searchUrl = $"https://lrclib.net/api/search?q={Uri.EscapeDataString(title + " " + artist)}";
            var searchResponse = await _httpClient.GetAsync(searchUrl);
            if (searchResponse.IsSuccessStatusCode)
            {
                var searchJson = await searchResponse.Content.ReadAsStringAsync();
                using var searchDoc = JsonDocument.Parse(searchJson);
                var searchRoot = searchDoc.RootElement;

                if (searchRoot.ValueKind == JsonValueKind.Array && searchRoot.GetArrayLength() > 0)
                {
                    foreach (var item in searchRoot.EnumerateArray())
                    {
                        if (item.TryGetProperty("syncedLyrics", out var itemSynced) && itemSynced.ValueKind == JsonValueKind.String)
                        {
                            var s = itemSynced.GetString();
                            if (!string.IsNullOrWhiteSpace(s)) return s;
                        }
                    }

                    // Fallback to first plain lyrics if no synced
                    var first = searchRoot[0];
                    if (first.TryGetProperty("plainLyrics", out var itemPlain) && itemPlain.ValueKind == JsonValueKind.String)
                    {
                        return itemPlain.GetString();
                    }
                }
            }
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"LRCLIB API exception: {ex.Message}");
        }

        return null;
    }

    public List<LyricLine> ParseLrc(string lrcContent)
    {
        var result = new List<LyricLine>();
        if (string.IsNullOrWhiteSpace(lrcContent)) return result;

        var lines = lrcContent.Split(new[] { "\r\n", "\r", "\n" }, StringSplitOptions.RemoveEmptyEntries);
        bool hasTimestamp = false;

        foreach (var rawLine in lines)
        {
            var match = LrcTimeRegex.Match(rawLine);
            if (match.Success)
            {
                hasTimestamp = true;
                int minutes = int.Parse(match.Groups[1].Value);
                int seconds = int.Parse(match.Groups[2].Value);
                string fracStr = match.Groups[3].Value;
                int millis = fracStr.Length == 2 ? int.Parse(fracStr) * 10 : int.Parse(fracStr);

                var time = TimeSpan.FromMinutes(minutes) + TimeSpan.FromSeconds(seconds) + TimeSpan.FromMilliseconds(millis);
                string text = match.Groups[4].Value.Trim();

                result.Add(new LyricLine(time, text));
            }
        }

        // If lyrics are plain text without timestamps, synthesize lines spaced evenly or as lines
        if (!hasTimestamp && lines.Length > 0)
        {
            for (int i = 0; i < lines.Length; i++)
            {
                var text = lines[i].Trim();
                if (!string.IsNullOrEmpty(text))
                {
                    result.Add(new LyricLine(TimeSpan.FromSeconds(i * 4), text));
                }
            }
        }

        result.Sort((a, b) => a.Timestamp.CompareTo(b.Timestamp));
        return result;
    }

    public int GetActiveIndex(List<LyricLine> lyrics, TimeSpan currentPosition, int offsetMs = 0)
    {
        if (lyrics == null || lyrics.Count == 0) return -1;

        var adjustedPosition = currentPosition + TimeSpan.FromMilliseconds(offsetMs);
        int active = -1;

        for (int i = 0; i < lyrics.Count; i++)
        {
            if (lyrics[i].Timestamp <= adjustedPosition)
            {
                active = i;
            }
            else
            {
                break;
            }
        }

        return active;
    }

    public static string CleanTrackTitle(string title)
    {
        if (string.IsNullOrWhiteSpace(title)) return string.Empty;
        var cleaned = CleanTitleRegex.Replace(title, string.Empty);
        // Remove trailing dashes or extra spaces
        cleaned = cleaned.Trim().TrimEnd('-', '|', '~', ':');
        return cleaned.Trim();
    }

    public static string CleanArtistName(string artist)
    {
        if (string.IsNullOrWhiteSpace(artist)) return string.Empty;
        // In YT Music sometimes artist has " - Topic"
        return artist.Replace(" - Topic", "", StringComparison.OrdinalIgnoreCase).Trim();
    }
}
