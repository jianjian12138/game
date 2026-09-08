"""
Audio-Visual Sync Deviation Meter
Real-time latency and beat drift visualizer for rhythm and action games.
"""

import math


class AudioSyncMeter:
    """Visualizes timing deviation between audio clock and visual render frames."""

    @staticmethod
    def render_gauge(deviation_ms: float, max_range_ms: float = 100.0, bar_width: int = 21) -> str:
        """
        Renders an ASCII needle gauge:
        [-100ms   0ms   +100ms]
        [---------|*--------] +25.0ms
        """
        half_w = bar_width // 2
        clamped_dev = max(-max_range_ms, min(max_range_ms, deviation_ms))
        ratio = clamped_dev / max_range_ms
        needle_pos = int(round(half_w + ratio * half_w))
        needle_pos = max(0, min(bar_width - 1, needle_pos))

        chars = ["-"] * bar_width
        chars[half_w] = "|"  # Zero line
        chars[needle_pos] = "*"

        bar_str = "".join(chars)
        status = "IN_SYNC" if abs(deviation_ms) <= 20.0 else ("AUDIO_EARLY" if deviation_ms < 0 else "AUDIO_LATE")
        return f"[{bar_str}] {deviation_ms:+.1f}ms ({status})"
