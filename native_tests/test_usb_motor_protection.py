import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from usb_motor_protection import MotorProtection


class ProtectionTests(unittest.TestCase):
    def test_peak_and_energy_bounds_at_supported_rates(self):
        for rate in (44100, 48000, 192000):
            engine = MotorProtection(rate)
            t = np.arange(rate // 2) / rate
            loud = np.column_stack((4 * np.sin(2 * np.pi * 160 * t),
                                    np.sin(2 * np.pi * 90 * t)))
            output = engine.process(loud, 100)
            self.assertLessEqual(float(np.max(np.abs(output))), .500001)
            self.assertTrue(np.all(np.sqrt(np.mean(output ** 2, axis=0)) <= .180001))

    def test_invalid_samples_and_silent_channel_do_not_leak(self):
        engine = MotorProtection(48000)
        samples = np.zeros((4800, 2))
        samples[:3, 0] = [np.nan, np.inf, -np.inf]
        output = engine.process(samples, 100)
        self.assertTrue(np.isfinite(output).all())
        self.assertEqual(np.count_nonzero(output), 0)

    def test_dc_removed_and_strength_adjustable(self):
        engine = MotorProtection(48000)
        output = engine.process(np.ones((48000, 2)) * .1, 100)
        self.assertLess(np.max(np.abs(output[-4800:])), 1e-6)
        t = np.arange(4800) / 48000
        signal = np.column_stack((.05 * np.sin(2 * np.pi * 160 * t), np.zeros(len(t))))
        engine = MotorProtection(48000)
        output = engine.process(signal, 25)
        self.assertAlmostEqual(engine.gain, .25)
        self.assertEqual(np.count_nonzero(output[:, 1]), 0)
        self.assertLess(np.max(np.abs(output[-480:])), .013)
        output = engine.process(signal, 0)
        self.assertAlmostEqual(engine.gain, 0)
        self.assertLess(np.max(np.abs(output[-48:])), .0005)

    def test_scheduled_rest_and_recovery(self):
        engine = MotorProtection(48000)
        engine.elapsed = engine.RUN_SECONDS
        self.assertEqual(np.count_nonzero(engine.process(np.ones((480, 2)), 100)), 0)
        self.assertTrue(engine.resting)
        engine.elapsed = engine.RUN_SECONDS + engine.REST_SECONDS
        t = np.arange(480) / 48000
        output = engine.process(np.column_stack((.05 * np.sin(2 * np.pi * 160 * t), t * 0)), 100)
        self.assertFalse(engine.resting)
        self.assertGreater(np.max(np.abs(output)), 0)


if __name__ == '__main__':
    unittest.main()
