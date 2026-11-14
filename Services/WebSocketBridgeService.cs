using System;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Media.Imaging;
using Notch.Models;

namespace Notch.Services;

public class WebSocketBridgeService
{
    private HttpListener? _httpListener;
    private CancellationTokenSource? _cts;
    private WebSocket? _activeClient;
    private readonly HttpClient _httpClient = new();

    public event Action<MediaTrack>? ExtensionTrackReceived;
    public event Action<TimeSpan>? ExtensionPositionReceived;
    public event Action<bool>? ClientConnectionChanged;

    public bool IsClientConnected => _activeClient != null && _activeClient.State == WebSocketState.Open;

    public void Start(int port = 7891)
    {
        Stop();

        _cts = new CancellationTokenSource();
        try
        {
            _httpListener = new HttpListener();
            _httpListener.Prefixes.Add($"http://127.0.0.1:{port}/");
            _httpListener.Start();

            _ = ListenAsync(_cts.Token);
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"Failed to start WebSocket server on port {port}: {ex.Message}");
        }
    }

    public void Stop()
    {
        _cts?.Cancel();
        try
        {
            _activeClient?.Dispose();
            _activeClient = null;
            _httpListener?.Stop();
            _httpListener?.Close();
        }
        catch { }
        finally
        {
            _httpListener = null;
            _cts = null;
            ClientConnectionChanged?.Invoke(false);
        }
    }

    private async Task ListenAsync(CancellationToken token)
    {
        while (!token.IsCancellationRequested && _httpListener != null && _httpListener.IsListening)
        {
            try
            {
                var context = await _httpListener.GetContextAsync();
                if (context.Request.IsWebSocketRequest)
                {
                    _ = ProcessWebSocketRequestAsync(context, token);
                }
                else
                {
                    // Respond with simple status check for health probe
                    context.Response.StatusCode = 200;
                    context.Response.ContentType = "application/json";
                    context.Response.Headers.Add("Access-Control-Allow-Origin", "*");
                    var statusBytes = Encoding.UTF8.GetBytes("{\"status\":\"ok\",\"service\":\"Notch Bridge\"}");
                    context.Response.OutputStream.Write(statusBytes, 0, statusBytes.Length);
                    context.Response.Close();
                }
            }
            catch (HttpListenerException) when (token.IsCancellationRequested)
            {
                break;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error accepting connection: {ex.Message}");
            }
        }
    }

    private async Task ProcessWebSocketRequestAsync(HttpListenerContext context, CancellationToken token)
    {
        try
        {
            var wsContext = await context.AcceptWebSocketAsync(subProtocol: null);
            _activeClient = wsContext.WebSocket;
            ClientConnectionChanged?.Invoke(true);

            var buffer = new byte[8192];
            while (_activeClient.State == WebSocketState.Open && !token.IsCancellationRequested)
            {
                using var ms = new MemoryStream();
                WebSocketReceiveResult result;
                do
                {
                    result = await _activeClient.ReceiveAsync(new ArraySegment<byte>(buffer), token);
                    if (result.MessageType == WebSocketMessageType.Close)
                    {
                        await _activeClient.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closing", token);
                        _activeClient = null;
                        ClientConnectionChanged?.Invoke(false);
                        return;
                    }
                    ms.Write(buffer, 0, result.Count);
                } while (!result.EndOfMessage);

                ms.Seek(0, SeekOrigin.Begin);
                var json = Encoding.UTF8.GetString(ms.ToArray());
                await HandleIncomingMessageAsync(json);
            }
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"WebSocket client error: {ex.Message}");
        }
        finally
        {
            _activeClient = null;
            ClientConnectionChanged?.Invoke(false);
        }
    }

    private async Task HandleIncomingMessageAsync(string json)
    {
        try
        {
            var message = JsonSerializer.Deserialize<ExtensionMessage>(json);
            if (message == null) return;

            if (message.Type == "position_update")
            {
                ExtensionPositionReceived?.Invoke(TimeSpan.FromSeconds(message.PositionSeconds));
                return;
            }

            BitmapImage? albumArt = null;
            if (!string.IsNullOrWhiteSpace(message.ArtUrl) && Uri.TryCreate(message.ArtUrl, UriKind.Absolute, out var artUri))
            {
                try
                {
                    var bytes = await _httpClient.GetByteArrayAsync(artUri);
                    using var stream = new MemoryStream(bytes);
                    var bmp = new BitmapImage();
                    bmp.BeginInit();
                    bmp.CacheOption = BitmapCacheOption.OnLoad;
                    bmp.StreamSource = stream;
                    bmp.EndInit();
                    bmp.Freeze();
                    albumArt = bmp;
                }
                catch { }
            }

            var track = new MediaTrack
            {
                Title = !string.IsNullOrWhiteSpace(message.Title) ? message.Title : "Unknown Track",
                Artist = !string.IsNullOrWhiteSpace(message.Artist) ? message.Artist : "Unknown Artist",
                Album = message.Album,
                Duration = TimeSpan.FromSeconds(message.DurationSeconds),
                Position = TimeSpan.FromSeconds(message.PositionSeconds),
                IsPlaying = message.IsPlaying,
                Source = message.Source,
                TrackId = message.TrackId,
                AlbumArt = albumArt,
                CanPlayPause = true,
                CanSkipNext = true,
                CanSkipPrevious = true
            };

            ExtensionTrackReceived?.Invoke(track);
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"Failed to parse extension message: {ex.Message}");
        }
    }

    public async Task SendCommandAsync(string command)
    {
        if (_activeClient != null && _activeClient.State == WebSocketState.Open)
        {
            try
            {
                var payload = JsonSerializer.Serialize(new { action = command });
                var bytes = Encoding.UTF8.GetBytes(payload);
                await _activeClient.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, CancellationToken.None);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Failed to send command to extension: {ex.Message}");
            }
        }
    }
}
