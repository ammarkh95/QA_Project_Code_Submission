"""
thermal_sim.py
--------------
Simulation-based testing interface of the theraml control subsystem
The module simulates the FW logic and exposes a simplified test interface emulating the firmware UART interface

Modelled behaviour
-------------------
* PWM duty cycle 0-100 % maps roughly linearly to fan RPM between FAN_MIN_RPM
  (stall) and FAN_MAX_RPM, with a small amount of noise.
* A closed-loop controller adjusts PWM to drive the measured temperature toward
  a target set point.
* Fault injection lets tests force realistic failure modes: stalled fan,
  disconnected tachometer, stuck I2C sensor, etc.
"""

from __future__ import annotations
from enum import Enum
from typing import Union

# Dervied constants from the FW requirements and subsystem desing specs
FAN_MAX_RPM = 6000      
FAN_MIN_RPM = 900 
PWM_MIN_SPIN = 10 # duty cycle %
PWM_STARTUP = 100 # duty cycle %
TACHO_TOLERANCE_PCT = 10 # %
TARGET_TEMP_C = 40.0
TEMP_MIN_C = 0.0
TEMP_MAX_C = 55.0


class ThermalSystemFaults(Enum):
    """
    Enumeration of Detected System ThermalSystemFaults (names mapped to error codes)    
    """
    @classmethod
    def list(cls):
        return list(map(lambda c: cls.__name__ + "." + c.name, cls))

    FAULT_FAN_FEEDBACK = 1  # tachometer signal reads zero due to broken tachometer sensor / fan not spinning
    FAULT_THERMAL_FEEDBACK = 2  # temperature sensor is faulty, invalid temperature readings


class ThermalControlSimulator:
    """Test Interface Simulator Class"""
    def __init__(self) -> None:
        self._target_temperature = TARGET_TEMP_C
        self._measured_temperature = None
        self._pwm_output_duty = PWM_STARTUP
        self._detected_faults_error_codes = []

    def get_fan_measured_rpm(self) -> Union[float, ThermalSystemFaults]:
        """
        Get Fan RPM speed based on tachometer feedback signal
        ideally matches with the commanded speed unless fault has occured then return Error code
        """
        # error case
        if ThermalSystemFaults.FAULT_FAN_FEEDBACK.value in self._detected_faults_error_codes:
            return ThermalSystemFaults.FAULT_FAN_FEEDBACK
        # matched case
        matched = self.get_expected_fan_rpm(self._pwm_output_duty)
        if matched == 0.0:
            return 0.0
        return max(0.0, matched)

    def get_expected_fan_rpm(self, duty: int) -> float:
        """Ideal RPM the firmware expects for a given PWM duty (no faults)."""
        if duty < PWM_MIN_SPIN:
            return 0.0
        frac = (duty - PWM_MIN_SPIN) / (100 - PWM_MIN_SPIN)
        return FAN_MIN_RPM + frac * (FAN_MAX_RPM - FAN_MIN_RPM)

    def attempt_temperature_read(self) -> Union[float, ThermalSystemFaults]:
        """
        Perform temperature read request
        ideally read temperature will drop due to cooling, else if thermal failure occured return an error
        """
        if ThermalSystemFaults.FAULT_THERMAL_FEEDBACK.value in self._detected_faults_error_codes:
            return ThermalSystemFaults.FAULT_THERMAL_FEEDBACK
        # Apply some cooling formula to simulate temperature drop
        cooling = (self._pwm_output_duty / 100.0) * 8.0
        self._measured_temperature += (self.target_temp - self._measured_temperature) * 0.05 - cooling * 0.02
        self._measured_temperature = max(TEMP_MIN_C, min(TEMP_MAX_C, self._measured_temperature))
        return round(self._measured_temperature, 2)

    def run_control_loop_iteration(self) -> None:
        """Process one control loop iteration"""
        response = self.attempt_temperature_read()
        # if temperature sensor failed -> # command 100% fan speed
        if isinstance(response, ThermalSystemFaults):
            if response.value == ThermalSystemFaults.FAULT_THERMAL_FEEDBACK.value:
                self._pwm_output_duty = 100
                return
        
        # adjust PWM output duty cycle to hold target temperature according to some control logical formula
        temp = response
        error = temp - self.target_temp
        self._pwm_output_duty = int(max(0, min(100, self.pwm_duty + error * 2)))

    #  simulate handling of FW commands 
    def command(self, cmd: str, par: str = None, value: any = None) -> any:
        """Process FW commands, return False if command is not a valid FW command or FW command failed"""

        if cmd == "GET":

            if par == "PWM_OUTPUT_DUTY":
                return (self._pwm_output_duty)
            
            if par == "TACHOMETER_RPM":
                response = self.get_fan_measured_rpm()
                if isinstance(response, ThermalSystemFaults):
                    if response.value == ThermalSystemFaults.FAULT_FAN_FEEDBACK.value:
                        return ("System Fault", ThermalSystemFaults.FAULT_FAN_FEEDBACK.value)
                return (int(round(response)))

            if par == "TEMPERATURE":
                response = self.attempt_temperature_read()
                if isinstance(response, ThermalSystemFaults):
                    if response.value == ThermalSystemFaults.FAULT_THERMAL_FEEDBACK.value:
                        return ("System Fault", ThermalSystemFaults.FAULT_THERMAL_FEEDBACK.value)
                return (response)

            return ("Error", f"Unknown FW GET parameter: {par}")

        if cmd == "SET":
            if par == "PWM_OUTPUT_DUTY":
                if not 0 <= value <= 100:
                    return ("Error", f"Invalid PWM duty cycle: {value} %")
                self._pwm_output_duty = value
                return True

            if par == "TARGET_TEMPERATURE":
                if not TEMP_MIN_C <= value <= TEMP_MAX_C:
                    return ("Error", f"Invalid Temperature value: {value}")
                self._target_temperature = value
                return True

            return ("Error", f"Unknown FW SET parameter: {par}")

        if cmd == "EXECUTE_CONTROL_LOOP":  # execute the control loop N times
            if value is not None and int(value) > 0:
                for _ in range(int(value)):
                    self.run_control_loop_iteration()
                return True
            return ("Error", f"Invalid Number of iterations: {value}for EXECUTE_CONTROL_LOOP")

        if cmd == "TRIGGER_FAULT":  # append an error to the list of detect error codes -> this falgs the FW that a fault has occured
            SUPPORTED_FAULTS = [f.value for f in ThermalSystemFaults]
            if value is not None and value in SUPPORTED_FAULTS:
                self._detected_faults_error_codes.append(value)
                return True
            
            return ("Error", f"Invalid/Undefined Fault Error code: {value} for TRIGGER_FAULT")

        return ("Error", f"Unknown FW command: {cmd}")

    # ---- helpers exposed to the fault CLI ---------------------------------
    def expected_rpm_for(self, duty: int) -> float:
        return self.get_expected_fan_rpm(duty)
