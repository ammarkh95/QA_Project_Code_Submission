*** Settings ***
Documentation     Sample FW Test code for the Thermal control subsystem Tacho-vs-PWM validation and fault test cases
...               robot tacho_validation.robot
Library           robot_keywords.py

*** Test Cases ***
Measured RPM Tracks Commanded PWM
    [Documentation]    REQ-4  Tacho within tolerance of the expected curve.
    [Template]    RPM Should Be Within Tolerance
    20
    40
    60
    80
    100

PWM Set And Read Back
    [Documentation]    REQ-XX  Duty is accepted and read back across the range.
    [Template]    PWM Round Trip Should Work
    0
    30
    60
    100


Fan Does Not Report Spin Below Minimum Duty
    [Documentation]     REQ-6  The FW shall command a 0% duty cycle for the PWM output signal if the requested duty cycle falls below the specified minimum spin threshold of the fan
    RPM At Duty Should Be Zero    5


