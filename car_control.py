
import time
import pygame
import numpy as np
import RPi.GPIO as GPIO

pygame.init()
pygame.joystick.init()

# Adjust
MAX_DUTY_CYCLE = 50
ANGULAR_MULTIPLIER = 0.3
TRIM_STEP = 0.01

# Initialize
joysticks = []

linear_speed = 0
angular_speed = 0

left_wheel_speed = 0
right_wheel_speed = 0

l_trim_multiplier = 1
r_trim_multiplier = 1

left_duty_cycle = 0
right_duty_cycle = 0

# Pins
INPUT1_LEFT = 21
INPUT2_LEFT = 20

INPUT3_RIGHT = 7
INPUT4_RIGHT = 8

ENABLE_LEFT = 12
ENABLE_RIGHT = 13

# Set pin modes
GPIO.setmode(GPIO.BCM)
GPIO.setup(INPUT1_LEFT, GPIO.OUT)
GPIO.setup(INPUT2_LEFT, GPIO.OUT)
GPIO.setup(INPUT3_RIGHT, GPIO.OUT)
GPIO.setup(INPUT4_RIGHT, GPIO.OUT)
GPIO.setup(ENABLE_LEFT, GPIO.OUT)
GPIO.setup(ENABLE_RIGHT, GPIO.OUT)

# Initialize PWM at 1 kHz
pwm_left = GPIO.PWM(ENABLE_LEFT, 1000)
pwm_left.start(0)
pwm_left.ChangeDutyCycle(0)

pwm_right = GPIO.PWM(ENABLE_RIGHT, 1000)
pwm_right.start(0)
pwm_right.ChangeDutyCycle(0)


def linear(joy):
    left_thumb = joy.get_axis(1)
    if left_thumb > 0.1:
        linear_speed = left_thumb
    elif left_thumb < -0.1:
        linear_speed = left_thumb
    else:
        linear_speed = 0
    return linear_speed


def angular(joy):
    right_thumb = joy.get_axis(2)
    if right_thumb > 0.1:
        angular_speed = right_thumb
    elif right_thumb < -0.1:
        angular_speed = right_thumb
    else:
        angular_speed = 0
    return angular_speed


def left_input(command):
    if command == "forward":
        GPIO.output(INPUT1_LEFT, GPIO.HIGH)
        GPIO.output(INPUT2_LEFT, GPIO.LOW)
    else:
        GPIO.output(INPUT1_LEFT, GPIO.LOW)
        GPIO.output(INPUT2_LEFT, GPIO.HIGH)


def right_input(command):
    if command == "forward":
        GPIO.output(INPUT3_RIGHT, GPIO.HIGH)
        GPIO.output(INPUT4_RIGHT, GPIO.LOW)
    else:
        GPIO.output(INPUT3_RIGHT, GPIO.LOW)
        GPIO.output(INPUT4_RIGHT, GPIO.HIGH)


def convert_to_pwm(left_dir, right_dir, left_wheel_speed, right_wheel_speed):
    right_duty_cycle = np.interp(
        right_wheel_speed, [0, 1+ANGULAR_MULTIPLIER], [0, MAX_DUTY_CYCLE])
    left_duty_cycle = np.interp(
        left_wheel_speed, [0, 1+ANGULAR_MULTIPLIER], [0, MAX_DUTY_CYCLE])

    if right_dir == 1 or right_dir == 0:
        right_input("forward")
    else:
        right_input("backward")
    if left_dir == 1 or left_dir == 0:
        left_input("forward")
    else:
        left_input("backward")

    return left_duty_cycle, right_duty_cycle


def trim(dir, l_trim_multiplier, r_trim_multiplier):
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
    l_trim_multiplier = 1
    r_trim_multiplier = 1
    return l_trim_multiplier, r_trim_multiplier


running = True
try:
    while running:
        for event in pygame.event.get():
            # Read events

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
            linear_speed = linear(joy)
            # Angular direction and speed from [0,1]
            angular_speed = angular(joy)

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
            angular_speed = angular_speed * ANGULAR_MULTIPLIER

            # Joystick Down
            if linear_speed > 0:
                left_wheel_speed = -linear_speed - angular_speed
                right_wheel_speed = -linear_speed + angular_speed

            # Joystick Up
            else:
                left_wheel_speed = -linear_speed + angular_speed
                right_wheel_speed = -linear_speed - angular_speed

        # Get final direction and magnitude of speed
        left_dir = np.sign(left_wheel_speed)
        right_dir = np.sign(right_wheel_speed)

        left_wheel_speed = np.abs(left_wheel_speed)
        right_wheel_speed = np.abs(right_wheel_speed)

        # Add boosts
        left_wheel_speed = left_wheel_speed*l_trim_multiplier
        right_wheel_speed = right_wheel_speed*r_trim_multiplier

        # Stop with no controller
        if not joysticks:
            left_wheel_speed = 0
            right_wheel_speed = 0

        # Write to input pins and get duty cycle
        left_duty_cycle, right_duty_cycle = convert_to_pwm(
            left_dir, right_dir, left_wheel_speed, right_wheel_speed)

        # Write to enablers

        pwm_left.ChangeDutyCycle(left_duty_cycle)
        pwm_right.ChangeDutyCycle(right_duty_cycle)

        # print(f"left: {left_duty_cycle} | speed: {left_wheel_speed}")
        # print(f"right: {right_duty_cycle} | speed {right_wheel_speed}")
        # print(f"right trim: {r_trim_multiplier} | left trim {l_trim_multiplier}")
        time.sleep(0.4)
finally:
    pwm_left.stop()
    pwm_right.stop()
    GPIO.cleanup()
