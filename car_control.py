#! /usr/bin/python

import pygame
import numpy as np

from gpiozero import Device, Motor
from gpiozero.pins.mock import MockFactory
try:
    import RPi.GPIO as GPIO
except Exception:
    import Mock.GPIO as GPIO
    Device.pin_factory = MockFactory()

# Pins
INPUT1_LEFT = 21
INPUT2_LEFT = 20

INPUT3_RIGHT = 7
INPUT4_RIGHT = 8

ENABLE_LEFT = 12
ENABLE_RIGHT = 13

# Adjust
MAX_DUTY_CYCLE = 0.50
MIN_DUTY_CYCLE = 0.10
ANGULAR_MULTIPLIER = 0.3
TRIM_STEP = 0.01

# Initialize
joysticks = []

l_trim_multiplier = 1
r_trim_multiplier = 1

# Motors
left_motors = Motor(forward=INPUT1_LEFT,
                    backward=INPUT2_LEFT, enable=ENABLE_LEFT)
right_motors = Motor(forward=INPUT3_RIGHT,
                     backward=INPUT4_RIGHT, enable=ENABLE_RIGHT)

# Init
pygame.init()
pygame.joystick.init()


def linear(joy):
    """Reads the left joystick value from -1 (up) to 1 (down)"""
    left_thumb = joy.get_axis(1)
    if left_thumb > 0.1:
        linear_speed = left_thumb
        thumb_dir = "backwards"
    elif left_thumb < -0.1:
        linear_speed = -left_thumb
        thumb_dir = "forwards"
    else:
        linear_speed = 0
        thumb_dir = ""
    return linear_speed, thumb_dir


def angular(joy):
    """Reads the right joystick value from -1 (left) to 1 (right)"""
    right_thumb = joy.get_axis(2)
    if right_thumb > 0.1:
        angular_speed = right_thumb
        ang_dir = "right"
    elif right_thumb < -0.1:
        angular_speed = -right_thumb
        ang_dir = "left"
    else:
        angular_speed = 0
        ang_dir = ""
    return angular_speed, ang_dir


def get_wheel_speeds(linear_speed, lin_dir, angular_speed, ang_dir):
    """Calculates independent wheel speeds for left and right sides"""
    left_wheel_speed, right_wheel_speed = linear_speed, linear_speed
    if lin_dir != "":
        angular_speed = np.interp(angular_speed, [0, 1], [
                                  0, linear_speed*ANGULAR_MULTIPLIER])
    if ang_dir == "right":
        left_wheel_speed += angular_speed
        right_wheel_speed -= angular_speed
    elif ang_dir == "left":
        left_wheel_speed -= angular_speed
        right_wheel_speed += angular_speed
    return left_wheel_speed, right_wheel_speed


def trim(dir, l_trim_multiplier, r_trim_multiplier):
    """Returns adjusted and clamped trim multipliers"""
    # Ensure good multipliers
    if l_trim_multiplier <= 0.5 or r_trim_multiplier <= 0.5:
        return l_trim_multiplier, r_trim_multiplier

    # Adjust for motor power differences
    if dir == "left":
        l_trim_multiplier -= TRIM_STEP
        r_trim_multiplier += TRIM_STEP
    else:
        l_trim_multiplier += TRIM_STEP
        r_trim_multiplier -= TRIM_STEP

    return l_trim_multiplier, r_trim_multiplier


def reset_trim(l_trim_multiplier, r_trim_multiplier):
    """Sets both trim values to 1"""
    l_trim_multiplier = 1
    r_trim_multiplier = 1
    return l_trim_multiplier, r_trim_multiplier


running = True
try:
    while running:
        # Read events
        for event in pygame.event.get():

            # Connect controller
            if event.type == pygame.JOYDEVICEADDED:
                print("Controller Connected")
                joy = pygame.joystick.Joystick(event.device_index)
                joysticks.append(joy)

            # Disconnect controller
            if event.type == pygame.JOYDEVICEREMOVED:
                print("Controller Disconnected")
                joysticks.clear()

        # Read joystick button presses and axis movements
        if joysticks:
            # Forward/backward direction and speed from [0,1]
            linear_speed, lin_dir = linear(joy)
            # Angular direction and speed from [0,1]
            angular_speed, ang_dir = angular(joy)

            # Check trim buttons
            if joy.get_hat(0)[0] == -1:  # Left-trim left
                l_trim_multiplier, r_trim_multiplier = trim(
                    "left", l_trim_multiplier, r_trim_multiplier)
            elif joy.get_hat(0)[0] == 1:  # Right-trim right
                l_trim_multiplier, r_trim_multiplier = trim(
                    "right", l_trim_multiplier, r_trim_multiplier)
            elif joy.get_hat(0)[1] == -1:  # Down-reset
                l_trim_multiplier, r_trim_multiplier = reset_trim(
                    l_trim_multiplier, r_trim_multiplier)

            # Calculate speeds

            left_wheel_speed, right_wheel_speed = get_wheel_speeds(
                linear_speed, lin_dir, angular_speed, ang_dir)

            # Add trim multipliers
            left_wheel_speed = left_wheel_speed*l_trim_multiplier
            right_wheel_speed = right_wheel_speed*r_trim_multiplier

            # Convert to pwm signal
            left_wheel_speed = np.interp(
                left_wheel_speed, [0, 1+ANGULAR_MULTIPLIER],
                [0, MAX_DUTY_CYCLE])

            # Write to input pins and get duty cycle
            if lin_dir == "forwards":
                left_motors.forward(left_wheel_speed)
                right_motors.forward(right_wheel_speed)
            elif lin_dir == "backwards":
                left_motors.backward(left_wheel_speed)
                right_motors.forward(right_wheel_speed)

        # Stop with no controller
        else:
            left_wheel_speed = right_wheel_speed = 0
            left_motors.stop()
            right_motors.stop()
        print(f"Left Motor: {left_motors.value}")
        print(f"Right Motor: {right_motors.value}")

finally:
    left_motors.close()
    right_motors.close()
    GPIO.cleanup()
