using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Notch.Services;

public static class ColorExtractor
{
    public static Color ExtractDominantColor(ImageSource? imageSource, Color defaultColor)
    {
        if (imageSource is not BitmapSource bitmap)
        {
            return defaultColor;
        }

        try
        {
            // Resize bitmap to a small 32x32 size for instant, lightweight color analysis
            var resized = new TransformedBitmap(bitmap, new ScaleTransform(
                32.0 / Math.Max(1, bitmap.PixelWidth),
                32.0 / Math.Max(1, bitmap.PixelHeight)));

            var formatConverted = new FormatConvertedBitmap(resized, PixelFormats.Bgra32, null, 0);

            int width = formatConverted.PixelWidth;
            int height = formatConverted.PixelHeight;
            int stride = width * 4;
            byte[] pixels = new byte[height * stride];
            formatConverted.CopyPixels(pixels, stride, 0);

            var colorBuckets = new Dictionary<int, (int count, long r, long g, long b)>();

            for (int i = 0; i < pixels.Length; i += 4)
            {
                byte b = pixels[i];
                byte g = pixels[i + 1];
                byte r = pixels[i + 2];
                byte a = pixels[i + 3];

                if (a < 128) continue; // Skip transparent pixels

                // Calculate brightness and saturation
                int max = Math.Max(r, Math.Max(g, b));
                int min = Math.Min(r, Math.Min(g, b));
                int delta = max - min;

                // Skip extremely dark (black) or extremely light (white/gray) pixels
                if (max < 30 || min > 240) continue;
                if (delta < 25) continue; // Low saturation (gray)

                // Quantize to 4-bit per channel
                int key = ((r >> 4) << 8) | ((g >> 4) << 4) | (b >> 4);

                if (!colorBuckets.TryGetValue(key, out var bucket))
                {
                    bucket = (0, 0, 0, 0);
                }

                // Give higher weight to colorful/saturated pixels
                int weight = 1 + (delta * 3 / 255);
                colorBuckets[key] = (bucket.count + weight, bucket.r + r * weight, bucket.g + g * weight, bucket.b + b * weight);
            }

            if (colorBuckets.Count > 0)
            {
                var best = colorBuckets.OrderByDescending(x => x.Value.count).First().Value;
                byte avgR = (byte)Math.Clamp(best.r / best.count, 0, 255);
                byte avgG = (byte)Math.Clamp(best.g / best.count, 0, 255);
                byte avgB = (byte)Math.Clamp(best.b / best.count, 0, 255);

                // Boost saturation if too dull for glass glow
                return BoostVibrance(Color.FromRgb(avgR, avgG, avgB));
            }
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"ColorExtractor error: {ex.Message}");
        }

        return defaultColor;
    }

    private static Color BoostVibrance(Color c)
    {
        // Convert to HSV, ensure minimum saturation and brightness for glass rim glow
        float r = c.R / 255f;
        float g = c.G / 255f;
        float b = c.B / 255f;

        float max = Math.Max(r, Math.Max(g, b));
        float min = Math.Min(r, Math.Min(g, b));
        float delta = max - min;

        float h = 0;
        if (delta > 0)
        {
            if (max == r) h = ((g - b) / delta) % 6;
            else if (max == g) h = ((b - r) / delta) + 2;
            else h = ((r - g) / delta) + 4;
            h *= 60;
            if (h < 0) h += 360;
        }

        float s = max == 0 ? 0 : delta / max;
        float v = max;

        // Ensure vibrant look for liquid glass glow
        s = Math.Clamp(s * 1.3f, 0.45f, 0.95f);
        v = Math.Clamp(v * 1.1f, 0.60f, 1.0f);

        // Convert back to RGB
        return HsvToRgb(h, s, v);
    }

    private static Color HsvToRgb(float h, float s, float v)
    {
        float c = v * s;
        float x = c * (1 - Math.Abs((h / 60) % 2 - 1));
        float m = v - c;

        float r = 0, g = 0, b = 0;
        if (h < 60) { r = c; g = x; b = 0; }
        else if (h < 120) { r = x; g = c; b = 0; }
        else if (h < 180) { r = 0; g = c; b = x; }
        else if (h < 240) { r = 0; g = x; b = c; }
        else if (h < 300) { r = x; g = 0; b = c; }
        else { r = c; g = 0; b = x; }

        return Color.FromRgb(
            (byte)((r + m) * 255),
            (byte)((g + m) * 255),
            (byte)((b + m) * 255)
        );
    }
}
