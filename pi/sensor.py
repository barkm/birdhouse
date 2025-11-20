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

    def __add__(self, other: "SensorData") -> "SensorData":
        return SensorData(
            temperature=self.temperature + other.temperature,
            humidity=self.humidity + other.humidity,
        )

    def __truediv__(self, divisor: float) -> "SensorData":
        return SensorData(
            temperature=self.temperature / divisor,
            humidity=self.humidity / divisor,
        )


def read_sensor_data(mock_data: bool) -> SensorData:
    read_sensor = mock_sensor_data if mock_data else read_hdc302x_sensor
    sensor_readings = [read_sensor() for _ in range(5)]
    return sum(sensor_readings, SensorData(0.0, 0.0)) / len(sensor_readings)


def read_hdc302x_sensor() -> SensorData:
    try:
        i2c = board.I2C()  # pyright: ignore[reportPossiblyUnboundVariable]
        sensor = adafruit_hdc302x.HDC302x(i2c)  # pyright: ignore[reportPossiblyUnboundVariable]
    except Exception:
        raise RuntimeError("Failed to initialize sensor")
    return SensorData(temperature=sensor.temperature, humidity=sensor.relative_humidity)


def mock_sensor_data() -> SensorData:
    temperature = 25 + random.random()
    humidity = 40 + random.random()
    return SensorData(temperature=temperature, humidity=humidity)
