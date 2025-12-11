# 3_6_switch_control.py

import RPi.GPIO as GPIO
import time

PWMA = 18; AIN1 = 22; AIN2 = 27
PWMB = 23; BIN1 = 25; BIN2 = 24

SW1 = 5
SW2 = 6
SW3 = 13
SW4 = 19

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

GPIO.setup(PWMA, GPIO.OUT); GPIO.setup(AIN1, GPIO.OUT); GPIO.setup(AIN2, GPIO.OUT)
GPIO.setup(PWMB, GPIO.OUT); GPIO.setup(BIN1, GPIO.OUT); GPIO.setup(BIN2, GPIO.OUT)

GPIO.setup(SW1, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(SW2, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(SW3, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(SW4, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

L_Motor = GPIO.PWM(PWMA, 500)
L_Motor.start(0)
R_Motor = GPIO.PWM(PWMB, 500)
R_Motor.start(0)

def move_forward():
    GPIO.output(AIN1, 0); GPIO.output(AIN2, 1)
    GPIO.output(BIN1, 0); GPIO.output(BIN2, 1)
    L_Motor.ChangeDutyCycle(50)
    R_Motor.ChangeDutyCycle(50)

def move_backward():
    GPIO.output(AIN1, 1); GPIO.output(AIN2, 0)
    GPIO.output(BIN1, 1); GPIO.output(BIN2, 0)
    L_Motor.ChangeDutyCycle(50)
    R_Motor.ChangeDutyCycle(50)

def turn_left():
    GPIO.output(AIN1, 1); GPIO.output(AIN2, 0)
    GPIO.output(BIN1, 0); GPIO.output(BIN2, 1)
    L_Motor.ChangeDutyCycle(50)
    R_Motor.ChangeDutyCycle(50)

def turn_right():
    GPIO.output(AIN1, 0); GPIO.output(AIN2, 1)
    GPIO.output(BIN1, 1); GPIO.output(BIN2, 0)
    L_Motor.ChangeDutyCycle(50)
    R_Motor.ChangeDutyCycle(50)

def stop():
    L_Motor.ChangeDutyCycle(0)
    R_Motor.ChangeDutyCycle(0)

try:
    while True:
        if GPIO.input(SW1) == GPIO.HIGH:
            print("SW1 : for")
            move_forward()
        elif GPIO.input(SW2) == GPIO.HIGH:
            print("SW2 : rig")
            turn_right()
        elif GPIO.input(SW3) == GPIO.HIGH:
            print("SW3 : lft")
            turn_left()
        elif GPIO.input(SW4) == GPIO.HIGH:
            print("SW4 : bck")
            move_backward()
        else:
            stop()
        
        time.sleep(0.01)

except KeyboardInterrupt:
    pass

GPIO.cleanup()