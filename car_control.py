
import time
import pygame
import numpy as np
import RPi.GPIO as GPIO

pygame.init()
pygame.joystick.init()

# Adjust
MAX_VOLTAGE = 5

# Initialize
joysticks = []
running = True
direction = "forward"
linear_speed = 0
angular_speed = 0
turning_dir = ""
left_wheel_speed = 0
right_wheel_speed = 0

# Pins
INPUT1_LEFT = 21
INPUT2_LEFT = 20
INPUT3_RIGHT = 7
INPUT4_RIGHT = 8
ENABLE_LEFT = 24
ENABLE_RIGHT = 23

#Set pin modes
GPIO.setmode(GPIO.BCM)
GPIO.setup(INPUT1_LEFT,GPIO.OUT)
GPIO.setup(INPUT2_LEFT,GPIO.OUT)
GPIO.setup(INPUT3_RIGHT,GPIO.OUT)
GPIO.setup(INPUT4_RIGHT,GPIO.OUT)
GPIO.setup(ENABLE_LEFT,GPIO.OUT)
GPIO.setup(ENABLE_RIGHT,GPIO.OUT)


def linear(joy):
    left_thumb = joy.get_axis(1)
    if left_thumb > 0.1:
        linear_speed = np.interp(left_thumb, [0, 1], [0, MAX_VOLTAGE/2])
        direction = "reverse"
    elif left_thumb < -0.1:
        linear_speed = np.interp(left_thumb, [-1, 0], [MAX_VOLTAGE/2, 0])
        direction = "forward"
    else:
        linear_speed = 0
        direction = "forward"
    return linear_speed, direction


def angular(joy):
    right_thumb = joy.get_axis(2)
    if right_thumb > 0.1:
        angular_speed = np.interp(right_thumb, [0, 1], [0, MAX_VOLTAGE/2])
        turning_dir = "right"
    elif right_thumb < -0.1:
        angular_speed = np.interp(right_thumb, [-1, 0], [MAX_VOLTAGE/2, 0])
        turning_dir = "left"
    else:
        angular_speed = 0
        turning_dir = ""
    return angular_speed, turning_dir


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
        linear_speed, direction = linear(joy)
        angular_speed, turning_dir = angular(joy)

        if direction == "forward":
            #Assign input Pins
            GPIO.output(INPUT1_LEFT,GPIO.HIGH)
            GPIO.output(INPUT2_LEFT,GPIO.LOW)
            GPIO.output(INPUT3_RIGHT,GPIO.HIGH)
            GPIO.output(INPUT4_RIGHT,GPIO.LOW)

            #Calculate speec
            left_wheel_speed = linear_speed
            right_wheel_speed = linear_speed
            if turning_dir == "right":
                left_wheel_speed += angular_speed
            else:
                right_wheel_speed += angular_speed
        else:
            #Assign input Pins
            GPIO.output(INPUT1_LEFT,GPIO.LOW)
            GPIO.output(INPUT2_LEFT,GPIO.HIGH)
            GPIO.output(INPUT3_RIGHT,GPIO.LOW)
            GPIO.output(INPUT4_RIGHT,GPIO.HIGH)

            #Calculate speed
            left_wheel_speed = -linear_speed
            right_wheel_speed = -linear_speed
            if turning_dir == "right":
                left_wheel_speed -= angular_speed
            else:
                right_wheel_speed -= angular_speed     
    
    #Stop with no controller
    if not joysticks:
        left_wheel_speed = 0
        right_wheel_speed = 0
    
    #Write to motors

    print(f"Forward Speed: {linear_speed}")
    print(f"Angular Speed: {angular_speed}")
    print(f"Direction: {direction}")
    time.sleep(0.2)
