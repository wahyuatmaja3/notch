from PyQt6.QtGui import QColor, QImage, QPixmap

def extract_accent_color(pixmap: QPixmap, default_hex="#1ED760") -> QColor:
    if not pixmap or pixmap.isNull():
        return QColor(default_hex)

    img = pixmap.toImage().scaled(32, 32)
    buckets = {}

    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            r, g, b, a = c.red(), c.green(), c.blue(), c.alpha()
            if a < 120:
                continue

            max_v = max(r, g, b)
            min_v = min(r, g, b)
            delta = max_v - min_v

            # Skip very dark or pure white/grey
            if max_v < 35 or min_v > 235 or delta < 25:
                continue

            # Quantize
            key = ((r >> 4) << 8) | ((g >> 4) << 4) | (b >> 4)
            weight = 1 + int(delta * 2 / 255)
            if key not in buckets:
                buckets[key] = [0, 0, 0, 0]
            buckets[key][0] += weight
            buckets[key][1] += r * weight
            buckets[key][2] += g * weight
            buckets[key][3] += b * weight

    if buckets:
        best = max(buckets.values(), key=lambda v: v[0])
        avg_r = int(best[1] / best[0])
        avg_g = int(best[2] / best[0])
        avg_b = int(best[3] / best[0])
        col = QColor(avg_r, avg_g, avg_b)
        # Ensure minimum saturation
        h, s, v, _ = col.getHsv()
        s = min(255, max(120, int(s * 1.3)))
        v = min(255, max(140, int(v * 1.1)))
        col.setHsv(h, s, v)
        return col

    return QColor(default_hex)
