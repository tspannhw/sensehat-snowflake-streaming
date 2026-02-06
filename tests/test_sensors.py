#!/usr/bin/env python3
"""
Tests for Sense HAT sensor reader.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sensehat_sensor import SenseHatSensor


class TestSenseHatSensor(unittest.TestCase):
    """Test cases for SenseHatSensor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.sensor = SenseHatSensor(simulate=True)

    def test_sensor_initialization(self):
        """Test sensor initializes correctly."""
        self.assertTrue(self.sensor.simulate)
        self.assertIsNotNone(self.sensor.hostname)
        self.assertIsNotNone(self.sensor.ip_address)
        self.assertIsNotNone(self.sensor.mac_address)

    def test_read_returns_dict(self):
        """Test read() returns a dictionary."""
        reading = self.sensor.read()
        self.assertIsInstance(reading, dict)

    def test_read_contains_required_fields(self):
        """Test reading contains all required fields."""
        reading = self.sensor.read()
        
        required_fields = [
            'uuid', 'rowid', 'hostname', 'ipaddress', 'macaddress',
            'ts', 'datetimestamp', 'systemtime',
            'temperature', 'humidity', 'pressure',
            'pitch', 'roll', 'yaw',
            'accel_x', 'accel_y', 'accel_z',
            'gyro_x', 'gyro_y', 'gyro_z',
            'mag_x', 'mag_y', 'mag_z', 'compass',
            'cpu_percent', 'memory_percent', 'disk_usage_mb',
            'cputempc', 'cputempf', 'simulated'
        ]
        
        for field in required_fields:
            self.assertIn(field, reading, f"Missing field: {field}")

    def test_temperature_range(self):
        """Test temperature is in reasonable range."""
        reading = self.sensor.read()
        self.assertGreater(reading['temperature'], -40)
        self.assertLess(reading['temperature'], 85)

    def test_humidity_range(self):
        """Test humidity is in valid range."""
        reading = self.sensor.read()
        self.assertGreaterEqual(reading['humidity'], 0)
        self.assertLessEqual(reading['humidity'], 100)

    def test_pressure_range(self):
        """Test pressure is in reasonable range."""
        reading = self.sensor.read()
        self.assertGreater(reading['pressure'], 800)
        self.assertLess(reading['pressure'], 1200)

    def test_orientation_range(self):
        """Test orientation values are in valid range."""
        reading = self.sensor.read()
        self.assertGreaterEqual(reading['yaw'], 0)
        self.assertLess(reading['yaw'], 360)

    def test_reading_count_increments(self):
        """Test reading count increments."""
        initial_count = self.sensor.reading_count
        self.sensor.read()
        self.assertEqual(self.sensor.reading_count, initial_count + 1)

    def test_multiple_reads(self):
        """Test multiple consecutive reads."""
        readings = [self.sensor.read() for _ in range(5)]
        self.assertEqual(len(readings), 5)
        
        uuids = [r['uuid'] for r in readings]
        self.assertEqual(len(uuids), len(set(uuids)), "UUIDs should be unique")

    def test_simulated_flag(self):
        """Test simulated flag is set correctly."""
        reading = self.sensor.read()
        self.assertTrue(reading['simulated'])

    def test_timestamp_format(self):
        """Test timestamp format is ISO 8601."""
        reading = self.sensor.read()
        self.assertIn('T', reading['datetimestamp'])
        self.assertIn(':', reading['datetimestamp'])


class TestSensorDataTypes(unittest.TestCase):
    """Test data types of sensor readings."""

    def setUp(self):
        self.sensor = SenseHatSensor(simulate=True)
        self.reading = self.sensor.read()

    def test_string_fields(self):
        """Test string fields are strings."""
        string_fields = ['uuid', 'rowid', 'hostname', 'ipaddress', 
                        'macaddress', 'datetimestamp', 'systemtime']
        for field in string_fields:
            self.assertIsInstance(self.reading[field], str, f"{field} should be string")

    def test_numeric_fields(self):
        """Test numeric fields are numbers."""
        numeric_fields = ['ts', 'temperature', 'humidity', 'pressure',
                         'pitch', 'roll', 'yaw', 'compass',
                         'accel_x', 'accel_y', 'accel_z',
                         'gyro_x', 'gyro_y', 'gyro_z',
                         'mag_x', 'mag_y', 'mag_z',
                         'cpu_percent', 'memory_percent', 'disk_usage_mb',
                         'cputempc', 'cputempf']
        for field in numeric_fields:
            self.assertIsInstance(self.reading[field], (int, float), 
                                f"{field} should be numeric")

    def test_boolean_fields(self):
        """Test boolean fields are booleans."""
        self.assertIsInstance(self.reading['simulated'], bool)


if __name__ == '__main__':
    print("=" * 60)
    print("Sense HAT Sensor Tests")
    print("=" * 60)
    unittest.main(verbosity=2)
