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


def read_sensor_data(mock_data: bool) -> SensorData:
    read_sensor = mock_sensor_data if mock_data else read_pi_sensor
    sensor_readings = [read_sensor() for _ in range(5)]
    return sum(sensor_readings, SensorData(0.0, 0.0, 0.0)) / len(sensor_readings)


def read_pi_sensor() -> SensorData:
    try:
        i2c = board.I2C()  # pyright: ignore[reportPossiblyUnboundVariable]
        sensor = adafruit_hdc302x.HDC302x(i2c)  # pyright: ignore[reportPossiblyUnboundVariable]
    except Exception:
        raise RuntimeError("Failed to initialize sensor")
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
