from dataclasses import dataclass
import random

try:
    import board  # pyright: ignore[reportMissingImports]
    import adafruit_hdc302x  # pyright: ignore[reportMissingImports]
except ImportError:
    pass


@dataclass
class SensorData:
    temperature: float
    humidity: float
    cpu_temperature: float = 0.0

    def __add__(self, other: "SensorData") -> "SensorData":
        return SensorData(
            temperature=self.temperature + other.temperature,
            humidity=self.humidity + other.humidity,
            cpu_temperature=self.cpu_temperature + other.cpu_temperature,
        )

    def __truediv__(self, divisor: float) -> "SensorData":
        return SensorData(
            temperature=self.temperature / divisor,
            humidity=self.humidity / divisor,
            cpu_temperature=self.cpu_temperature / divisor,
        )


@dataclass
class SensorStatus:
    raw_value: int
    alert_active: bool
    heater_on: bool
    relative_humidity_alert: bool
    temperature_alert: bool
    reset_detected: bool
    checksum_error: bool


def read_sensor_data(mock_data: bool) -> SensorData:
    read_sensor = mock_sensor_data if mock_data else read_pi_sensor
    sensor_readings = [read_sensor() for _ in range(5)]
    return sum(sensor_readings, SensorData(0.0, 0.0, 0.0)) / len(sensor_readings)


def get_sensor():
    try:
        i2c = board.I2C()  # pyright: ignore[reportPossiblyUnboundVariable]
        return adafruit_hdc302x.HDC302x(i2c)  # pyright: ignore[reportPossiblyUnboundVariable]
    except Exception:
        raise RuntimeError("Failed to initialize sensor")


def has_sensor() -> bool:
    try:
        get_sensor()
        return True
    except RuntimeError:
        return False


def read_pi_sensor_status() -> SensorStatus:
    sensor = get_sensor()
    return parse_hdc302x_status(sensor.status)


def parse_hdc302x_status(status_int: int) -> SensorStatus:
    """
    Parses the 16-bit integer status from the HDC302x into a readable dataclass.
    """
    return SensorStatus(
        raw_value=status_int,
        alert_active=bool(status_int & (1 << 15)),
        heater_on=bool(status_int & (1 << 13)),
        relative_humidity_alert=bool(status_int & (1 << 11)),
        temperature_alert=bool(status_int & (1 << 10)),
        reset_detected=bool(status_int & (1 << 4)),
        checksum_error=bool(status_int & (1 << 0)),
    )


def read_pi_sensor() -> SensorData:
    sensor = get_sensor()
    return SensorData(
        temperature=sensor.temperature,
        humidity=sensor.relative_humidity,
        cpu_temperature=read_cpu_temperature(),
    )


def read_cpu_temperature() -> float:
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp_str = f.read().strip()
            return float(temp_str) / 1000.0
    except Exception:
        raise RuntimeError("Failed to read CPU temperature")


def mock_sensor_data() -> SensorData:
    temperature = 25 + random.random()
    humidity = 40 + random.random()
    cpu_temperature = 50 + random.random()
    return SensorData(
        temperature=temperature, humidity=humidity, cpu_temperature=cpu_temperature
    )
