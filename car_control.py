
import time
import pygame
import numpy as np
import RPi.GPIO as GPIO

pygame.init()
pygame.joystick.init()
GPIO.cleanup()

# Adjust
MAX_DUTY_CYCLE = 50

# Initialize
joysticks = []

lin_direction = "forward"
turn_direction = ""

linear_speed = 0
angular_speed = 0

left_wheel_speed = 0
right_wheel_speed = 0

left_duty_cycle = 0
right_duty_cycle = 0

# Pins
INPUT1_LEFT = 21
INPUT2_LEFT = 20

INPUT3_RIGHT = 7
INPUT4_RIGHT = 8

ENABLE_LEFT = 24
ENABLE_RIGHT = 23

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

pwm_right = GPIO.PWM(ENABLE_RIGHT, 1000)
pwm_right.start(0)


def linear(joy):
    left_thumb = joy.get_axis(1)
    if left_thumb > 0.1:
        linear_speed = left_thumb
        lin_direction = "reverse"
    elif left_thumb < -0.1:
        linear_speed = left_thumb*-1
        lin_direction = "forward"
    else:
        linear_speed = 0
        lin_direction = "forward"
    return linear_speed, lin_direction


def angular(joy):
    right_thumb = joy.get_axis(2)
    if right_thumb > 0.1:
        angular_speed = right_thumb
        turn_direction = "right"
    elif right_thumb < -0.1:
        angular_speed = right_thumb*-1
        turn_direction = "left"
    else:
        angular_speed = 0
        turn_direction = ""
    return angular_speed, turn_direction


def set_forward(linear_speed, angular_speed, turn_direction):
    # Assign input Pins
    GPIO.output(INPUT1_LEFT, GPIO.HIGH)
    GPIO.output(INPUT2_LEFT, GPIO.LOW)

    GPIO.output(INPUT3_RIGHT, GPIO.HIGH)
    GPIO.output(INPUT4_RIGHT, GPIO.LOW)

    # Calculate speec
    left_wheel_speed = linear_speed
    right_wheel_speed = linear_speed
    if turn_direction == "right":
        left_wheel_speed += angular_speed
    else:
        right_wheel_speed += angular_speed
    return left_wheel_speed, right_wheel_speed


def set_backward(linear_speed, angular_speed, turn_direction):
    # Assign input Pins
    GPIO.output(INPUT1_LEFT, GPIO.LOW)
    GPIO.output(INPUT2_LEFT, GPIO.HIGH)

    GPIO.output(INPUT3_RIGHT, GPIO.LOW)
    GPIO.output(INPUT4_RIGHT, GPIO.HIGH)

    # Calculate speed
    left_wheel_speed = linear_speed
    right_wheel_speed = linear_speed
    if turn_direction == "right":
        left_wheel_speed -= angular_speed
    else:
        right_wheel_speed -= angular_speed
    return left_wheel_speed, right_wheel_speed


def convert_to_pwm(left_wheel_speed, right_wheel_speed):
    left_duty_cycle = np.interp(
        left_wheel_speed, [0, 1], [0, MAX_DUTY_CYCLE])
    right_duty_cycle = np.interp(
        right_wheel_speed, [0, 1], [0, MAX_DUTY_CYCLE])
    return left_duty_cycle, right_duty_cycle


running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.JOYDEVICEADDED:
            print("Controller Connected")
            joy = pygame.joystick.Joystick(event.device_index)
            joysticks.append(joy)

        if event.type == pygame.JOYDEVICEREMOVED:
            print("Controller Disconnected")
            joysticks.clear()

    if joysticks:
        # Forward/backward and left/right
        linear_speed, lin_direction = linear(joy)
        angular_speed, turn_direction = angular(joy)

        if lin_direction == "forward":
            left_wheel_speed, right_wheel_speed = set_forward(
                linear_speed, angular_speed, turn_direction)
        else:
            left_wheel_speed, right_wheel_speed = set_backward(
                linear_speed, angular_speed, turn_direction)

    # Stop with no controller
    if not joysticks:
        left_wheel_speed = 0
        right_wheel_speed = 0

    # Write to motors
    left_duty_cycle, right_duty_cycle = convert_to_pwm(
        left_wheel_speed, right_wheel_speed)
    pwm_left.ChangeDutyCycle(left_duty_cycle)
    pwm_right.ChangeDutyCycle(right_duty_cycle)

    # print(f"left: {left_duty_cycle}")
    # print(f"right: {right_duty_cycle}")
    # print(f"Linear direction: {lin_direction}")
    # print(f"Angular direction: {turn_direction}")
    # print(f"1: {INPUT1_LEFT}")
    # print(f"2: {inp}")
    # print(f"3: {lin_direction}")
    # print(f"4: {turn_direction}")
