"""Conservative software bounds for the native helper's motor feed only."""
import math

import numpy as np


class MotorProtection:
    PEAK_LIMIT = 0.5
    RMS_LIMIT = 0.18
    RUN_SECONDS = 20 * 60
    REST_SECONDS = 30

    def __init__(self, rate):
        self.rate = rate
        self.gain = 0.0
        self.previous_input = np.zeros(2)
        self.previous_dc = np.zeros(2)
        self.elapsed = 0.0
        self.limited = False
        self.resting = False

    def process(self, samples, strength):
        # Bounded chunks keep the vectorized recursive DC blocker well conditioned.
        source = np.asarray(samples, dtype=np.float64)
        result = np.zeros_like(source, dtype=np.float32)
        self.limited = False
        for start in range(0, len(source), max(1, self.rate // 100)):
            x = np.nan_to_num(source[start:start + max(1, self.rate // 100)],
                              nan=0.0, posinf=0.0, neginf=0.0)
            x = np.clip(x, -1.0, 1.0)
            count = len(x)
            r = math.exp(-2 * math.pi * 20 / self.rate)
            powers = r ** np.arange(1, count + 1)
            differences = np.diff(np.vstack((self.previous_input, x)), axis=0)
            dc = powers[:, None] * (self.previous_dc +
                  np.cumsum(differences / powers[:, None], axis=0))
            self.previous_input = x[-1].copy()
            self.previous_dc = dc[-1].copy()
            # A scheduled rest is based on running time, even during quiet passages.
            cycle = self.RUN_SECONDS + self.REST_SECONDS
            positions = (self.elapsed + np.arange(count) / self.rate) % cycle
            rest_envelope = np.minimum(np.clip((self.RUN_SECONDS - positions) / .1, 0, 1),
                                       np.clip(positions / .1, 0, 1))
            rest_envelope[positions >= self.RUN_SECONDS] = 0
            self.resting = bool(positions[-1] >= self.RUN_SECONDS)
            target = float(np.clip(strength, 0, 100)) / 100
            step = 1 / (self.rate * .1)
            gains = self.gain + np.clip(target - self.gain,
                                      -step * np.arange(1, count + 1),
                                      step * np.arange(1, count + 1))
            self.gain = gains[-1]
            motor = dc * (gains * rest_envelope)[:, None]
            peak = np.max(np.abs(motor), axis=0)
            rms = np.sqrt(np.mean(motor * motor, axis=0))
            scale = np.minimum(1, np.minimum(self.PEAK_LIMIT / np.maximum(peak, 1e-12),
                                           self.RMS_LIMIT / np.maximum(rms, 1e-12)))
            self.limited |= bool(np.any(scale < 1))
            result[start:start + count] = np.clip(motor * scale, -self.PEAK_LIMIT, self.PEAK_LIMIT)
            self.elapsed += count / self.rate
        return result
