"""
robot_keywords.py
-----------------
Keyword library backing tacho_validation.robot. Shares the same simulator and
transport as the pytest suite so both front-ends validate one device model.
"""

from robot.api.deco import keyword  # provided by the `robotframework` package

from thermal_control_simulator import ThermalControlSimulator, TACHO_TOLERANCE_PCT

_dev = None


def _device() -> ThermalControlSimulator:
    global _dev
    if _dev is None:
        _dev = ThermalControlSimulator()
    return _dev


@keyword
def pwm_round_trip_should_work(duty):
    d = _device()
    assert d.command("SET", "PWM_OUTPUT_DUTY", int(duty)) == True
    got = int(d.command("GET", "PWM_OUTPUT_DUTY"))
    assert got == int(duty), f"read back {got}, expected {duty}"


@keyword
def rpm_should_be_within_tolerance(duty, tolerance_pct= TACHO_TOLERANCE_PCT):
    d = _device()
    assert d.command("SET", "PWM_OUTPUT_DUTY", int(duty)) == True
    expected = d.get_expected_fan_rpm(int(duty))
    measured = float(d.command("GET", "TACHOMETER_RPM"))
    tol = expected * float(tolerance_pct) / 100.0
    assert abs(measured - expected) <= tol, (
        f"duty {duty}%: {measured:.0f} RPM outside {expected:.0f} +/- {tol:.0f}")


@keyword
def rpm_at_duty_should_be_zero(duty):
    d = _device()
    assert d.command("SET", "PWM_OUTPUT_DUTY", int(duty)) == True
    rpm = float(d.command("GET", "TACHOMETER_RPM"))
    assert rpm == 0, f"expected 0 RPM at duty {duty}%, got {rpm}"
