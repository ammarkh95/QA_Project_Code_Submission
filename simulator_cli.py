"""
fault_simulator_cli.py
------------
a command-line tool based on ThermalControlSimulator interface. it checks:
    - log PWM duty , expected and mesaured RPM data of the system
    - perform a tolerance check 

Examples
--------
Run full duty range cycle PWM 0->100 and log tacho readings to CSV:
    python simulator_cli.py sweep --step 10 --out logs/pwm_vs_rpm_sweep.csv

Run a tacho tolerance check for a given PWM duty cycle and accepted tolerance %:
    python simulator_cli.py check --duty 60 --tolerance 10
"""

from __future__ import annotations

import argparse
import csv
import os

from thermal_control_simulator import ThermalControlSimulator, TACHO_TOLERANCE_PCT


def _dev() -> ThermalControlSimulator:
    d = ThermalControlSimulator()
    return d


def cmd_sweep(args) -> int:
    """Log data PWM Duty vs. mesured and expected RPM speed"""
    d = _dev()
    rows = []
    # loop through duty cycle range in fixed steps
    for duty in range(0, 101, args.step):
        d.command("SET", "PWM_OUTPUT_DUTY", int(duty))
        rpm = int(float(d.command("GET", "TACHOMETER_RPM")))
        expected = int(round(d.get_expected_fan_rpm(int(duty))))
        # save data
        rows.append((duty, expected, rpm))
        print(f"duty={duty:3d}%  expected={expected:5d} RPM  measured={rpm:5d} RPM")
    # output log file in form of .csv file
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["pwm_duty_pct", "expected_rpm", "measured_rpm"])
            w.writerows(rows)
        print(f"\nWrote {len(rows)} rows to {args.out}")
    return 0


def cmd_check(args) -> int:
    """Tacho RPM tolerance check"""
    d = _dev()
    d.command("SET", "PWM_OUTPUT_DUTY", int(args.duty))
    expected =  d.get_expected_fan_rpm(int(args.duty))
    measured = float(d.command("GET", "TACHOMETER_RPM"))
    tol = expected * args.tolerance / 100.0
    is_within_tolerance = abs(measured - expected) <= tol
    status = "PASS" if is_within_tolerance else "FAIL"
    print(f"[{status}] duty={args.duty}%  measured={measured:.0f} RPM  "
          f"expected={expected:.0f} +/- {tol:.0f} RPM")
    return 0 if is_within_tolerance else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Thermal subsystem fault/log CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)


    sp = sub.add_parser("sweep", parents=[common], help="sweep PWM duty range and log expected and measured RPM speed")
    sp.add_argument("--step", type=int, default=10)
    sp.add_argument("--out", default="")
    sp.set_defaults(func=cmd_sweep)

    cp = sub.add_parser("check", parents=[common], help="tacho tolerance check")
    cp.add_argument("--duty", type=int, default=60)
    cp.add_argument("--tolerance", type=float, default=TACHO_TOLERANCE_PCT)
    cp.set_defaults(func=cmd_check)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
   main()
