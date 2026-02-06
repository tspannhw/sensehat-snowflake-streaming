#!/usr/bin/env python3
"""
Raspberry Pi Sense HAT Sensor Reader
Reads environmental and IMU data from Sense HAT.
Supports simulation mode for testing without hardware.
Optimized for 2GB RAM Raspberry Pi.
"""

import time
import uuid
import socket
import logging
import random
from datetime import datetime, timezone
from typing import Dict, Optional

logger = logging.getLogger(__name__)

try:
    from sense_hat import SenseHat
    HAS_SENSEHAT = True
except ImportError:
    HAS_SENSEHAT = False
    logger.warning("sense_hat not available - using simulation mode")

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class SenseHatSensor:
    """
    Sense HAT sensor reader with simulation fallback.
    """

    def __init__(self, simulate: bool = False):
        self.simulate = simulate or not HAS_SENSEHAT
        self.sense = None
        self.hostname = socket.gethostname()

        try:
            self.ip_address = socket.gethostbyname(socket.gethostname())
        except Exception:
            self.ip_address = "127.0.0.1"

        self.mac_address = self._get_mac_address()
        self.reading_count = 0

        if not self.simulate and HAS_SENSEHAT:
            try:
                self.sense = SenseHat()
                self.sense.clear()
                logger.info("Sense HAT initialized")
            except Exception as e:
                logger.warning(f"Failed to init Sense HAT: {e} - using simulation")
                self.simulate = True
        else:
            logger.info("Running in SIMULATION mode")

    def _get_mac_address(self) -> str:
        """Get MAC address."""
        try:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff)
                          for ele in range(0, 48, 8)][::-1])
            return mac
        except Exception:
            return "00:00:00:00:00:00"

    def _get_system_metrics(self) -> Dict:
        """Get CPU, memory, disk usage."""
        metrics = {
            'cpu_percent': 0.0,
            'memory_percent': 0.0,
            'disk_usage_mb': 0.0,
            'cpu_temp_c': 0.0,
            'cpu_temp_f': 32.0
        }

        if HAS_PSUTIL:
            try:
                metrics['cpu_percent'] = psutil.cpu_percent(interval=0.1)
                metrics['memory_percent'] = psutil.virtual_memory().percent
                metrics['disk_usage_mb'] = psutil.disk_usage('/').used / (1024 * 1024)
            except Exception:
                pass

        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp_milli = int(f.read().strip())
                metrics['cpu_temp_c'] = temp_milli / 1000.0
                metrics['cpu_temp_f'] = (metrics['cpu_temp_c'] * 9/5) + 32
        except Exception:
            pass

        return metrics

    def _simulate_reading(self) -> Dict:
        """Generate simulated sensor data."""
        base_temp = 22.0 + random.gauss(0, 2)
        base_humidity = 45.0 + random.gauss(0, 5)
        base_pressure = 1013.25 + random.gauss(0, 5)

        return {
            'temperature': round(base_temp, 2),
            'humidity': round(max(0, min(100, base_humidity)), 2),
            'pressure': round(base_pressure, 2),
            'pitch': round(random.uniform(-5, 5), 2),
            'roll': round(random.uniform(-5, 5), 2),
            'yaw': round(random.uniform(0, 360), 2),
            'accel_x': round(random.gauss(0, 0.1), 4),
            'accel_y': round(random.gauss(0, 0.1), 4),
            'accel_z': round(1.0 + random.gauss(0, 0.05), 4),
            'gyro_x': round(random.gauss(0, 1), 4),
            'gyro_y': round(random.gauss(0, 1), 4),
            'gyro_z': round(random.gauss(0, 1), 4),
            'mag_x': round(random.gauss(20, 5), 4),
            'mag_y': round(random.gauss(-10, 5), 4),
            'mag_z': round(random.gauss(-50, 10), 4),
            'compass': round(random.uniform(0, 360), 2)
        }

    def _read_real_sensors(self) -> Dict:
        """Read from actual Sense HAT hardware."""
        temperature = self.sense.get_temperature()
        humidity = self.sense.get_humidity()
        pressure = self.sense.get_pressure()

        orientation = self.sense.get_orientation()
        accel = self.sense.get_accelerometer_raw()
        gyro = self.sense.get_gyroscope_raw()
        mag = self.sense.get_compass_raw()
        compass = self.sense.get_compass()

        return {
            'temperature': round(temperature, 2),
            'humidity': round(humidity, 2),
            'pressure': round(pressure, 2),
            'pitch': round(orientation.get('pitch', 0), 2),
            'roll': round(orientation.get('roll', 0), 2),
            'yaw': round(orientation.get('yaw', 0), 2),
            'accel_x': round(accel.get('x', 0), 4),
            'accel_y': round(accel.get('y', 0), 4),
            'accel_z': round(accel.get('z', 0), 4),
            'gyro_x': round(gyro.get('x', 0), 4),
            'gyro_y': round(gyro.get('y', 0), 4),
            'gyro_z': round(gyro.get('z', 0), 4),
            'mag_x': round(mag.get('x', 0), 4),
            'mag_y': round(mag.get('y', 0), 4),
            'mag_z': round(mag.get('z', 0), 4),
            'compass': round(compass, 2)
        }

    def read(self) -> Dict:
        """Read all sensor data and return as dictionary for Snowflake."""
        self.reading_count += 1
        now = datetime.now(timezone.utc)
        ts_epoch = int(time.time())

        if self.simulate:
            sensor_data = self._simulate_reading()
        else:
            try:
                sensor_data = self._read_real_sensors()
            except Exception as e:
                logger.error(f"Sensor read error: {e}")
                sensor_data = self._simulate_reading()

        system = self._get_system_metrics()

        reading = {
            'uuid': f"sensehat_{self.hostname}_{now.strftime('%Y%m%d%H%M%S')}_{self.reading_count}",
            'rowid': f"{now.strftime('%Y%m%d%H%M%S')}_{uuid.uuid4()}",
            'hostname': self.hostname,
            'ipaddress': self.ip_address,
            'macaddress': self.mac_address,
            'ts': ts_epoch,
            'datetimestamp': now.isoformat(),
            'systemtime': now.strftime('%m/%d/%Y %H:%M:%S'),
            'temperature': sensor_data['temperature'],
            'humidity': sensor_data['humidity'],
            'pressure': sensor_data['pressure'],
            'pitch': sensor_data['pitch'],
            'roll': sensor_data['roll'],
            'yaw': sensor_data['yaw'],
            'accel_x': sensor_data['accel_x'],
            'accel_y': sensor_data['accel_y'],
            'accel_z': sensor_data['accel_z'],
            'gyro_x': sensor_data['gyro_x'],
            'gyro_y': sensor_data['gyro_y'],
            'gyro_z': sensor_data['gyro_z'],
            'mag_x': sensor_data['mag_x'],
            'mag_y': sensor_data['mag_y'],
            'mag_z': sensor_data['mag_z'],
            'compass': sensor_data['compass'],
            'cpu_percent': round(system['cpu_percent'], 1),
            'memory_percent': round(system['memory_percent'], 1),
            'disk_usage_mb': round(system['disk_usage_mb'], 1),
            'cputempc': round(system['cpu_temp_c'], 1),
            'cputempf': round(system['cpu_temp_f'], 1),
            'simulated': self.simulate
        }

        return reading

    def display_reading(self, reading: Dict):
        """Display reading on Sense HAT LED matrix (temperature color)."""
        if self.sense and not self.simulate:
            temp = reading.get('temperature', 20)
            if temp < 15:
                color = (0, 0, 255)
            elif temp < 25:
                color = (0, 255, 0)
            elif temp < 30:
                color = (255, 255, 0)
            else:
                color = (255, 0, 0)
            self.sense.clear(color)

    def clear_display(self):
        """Clear the LED matrix."""
        if self.sense:
            self.sense.clear()


def main():
    """Test the sensor reader."""
    logging.basicConfig(level=logging.INFO)
    sensor = SenseHatSensor(simulate=True)

    print("Reading sensor data (Ctrl+C to stop)...")
    try:
        while True:
            reading = sensor.read()
            print(f"Temp: {reading['temperature']:.1f}C, "
                  f"Humidity: {reading['humidity']:.1f}%, "
                  f"Pressure: {reading['pressure']:.1f}mb, "
                  f"Pitch: {reading['pitch']:.1f}, "
                  f"Roll: {reading['roll']:.1f}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped")
        sensor.clear_display()


if __name__ == '__main__':
    main()
