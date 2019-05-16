from __future__ import absolute_import

import time
import unittest

from core.timeout import Timeout
from core.timestamp import Timestamp
from pyipv8.ipv8.util import old_round


class TimeoutTestSuite(unittest.TestCase):
    """Timeout test cases."""

    def setUp(self):
        # Object creation
        self.timeout1 = Timeout(3600)
        self.timeout2 = Timeout(120)

    def test_init(self):
        # Test for init validation
        with self.assertRaises(ValueError):
            Timeout(-1.0)
        with self.assertRaises(ValueError):
            Timeout("1")

    def test_timed_out(self):
        # Test for timed out
        self.assertTrue(self.timeout1.is_timed_out(Timestamp(int(old_round(time.time() * 1000)) - 3700 * 1000)))
        self.assertFalse(self.timeout2.is_timed_out(Timestamp(int(old_round(time.time() * 1000)))))

    def test_hash(self):
        # Test for hashes
        self.assertEqual(self.timeout1.__hash__(), Timeout(3600).__hash__())
        self.assertNotEqual(self.timeout1.__hash__(), self.timeout2.__hash__())