import threading
import time
import RPi.GPIO as GPIO

class Drive:
    def __init__(self):
        self.pins = {"SW1":5,"SW2":6,"SW3":13,"SW4":19,"PWMA":18,"AIN1":22,"AIN2":27,"PWMB":23,"BIN1":25,"BIN2":24}    
        self.config_GPIO()
        self.L_Motor = GPIO.PWM(self.pins["PWMA"],500)
        self.L_Motor.start(0)
        self.R_Motor = GPIO.PWM(self.pins["PWMB"],500)
        self.R_Motor.start(0)

    def config_GPIO(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pins["SW1"],GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(self.pins["SW2"],GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(self.pins["SW3"],GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(self.pins["SW4"],GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(self.pins["PWMA"],GPIO.OUT)
        GPIO.setup(self.pins["AIN1"],GPIO.OUT)
        GPIO.setup(self.pins["AIN2"],GPIO.OUT)
        GPIO.setup(self.pins["PWMB"],GPIO.OUT)
        GPIO.setup(self.pins["BIN1"],GPIO.OUT)
        GPIO.setup(self.pins["BIN2"],GPIO.OUT)

    def clean_GPIO(self):
        GPIO.cleanup()
    
    def motor_go(self, speed):
        GPIO.output(self.pins["AIN1"],0)
        GPIO.output(self.pins["AIN2"],1)
        self.L_Motor.ChangeDutyCycle(speed)
        GPIO.output(self.pins["BIN1"],0)
        GPIO.output(self.pins["BIN2"],1)
        self.R_Motor.ChangeDutyCycle(speed)

    def motor_back(self, speed):
        GPIO.output(self.pins["AIN1"],1)
        GPIO.output(self.pins["AIN2"],0)
        self.L_Motor.ChangeDutyCycle(speed)
        GPIO.output(self.pins["BIN1"],1)
        GPIO.output(self.pins["BIN2"],0)
        self.R_Motor.ChangeDutyCycle(speed)
        
    def motor_left(self, speed):
        GPIO.output(self.pins["AIN1"],1)
        GPIO.output(self.pins["AIN2"],0)
        self.L_Motor.ChangeDutyCycle(speed)
        GPIO.output(self.pins["BIN1"],0)
        GPIO.output(self.pins["BIN2"],1)
        self.R_Motor.ChangeDutyCycle(speed)
        
    def motor_right(self, speed):
        GPIO.output(self.pins["AIN1"],0)
        GPIO.output(self.pins["AIN2"],1)
        self.L_Motor.ChangeDutyCycle(speed)
        GPIO.output(self.pins["BIN1"],1)
        GPIO.output(self.pins["BIN2"],0)
        self.R_Motor.ChangeDutyCycle(speed)

    def motor_stop(self):
        GPIO.output(self.pins["AIN1"],0)
        GPIO.output(self.pins["AIN2"],1)
        self.L_Motor.ChangeDutyCycle(0)
        GPIO.output(self.pins["BIN1"],0)
        GPIO.output(self.pins["BIN2"],1)
        self.R_Motor.ChangeDutyCycle(0)

if __name__ == '__main__':

    drive = Drive()
    drive.motor_go(40)
    time.sleep(2)
    drive.motor_left(40)
    time.sleep(2)
    drive.motor_right(40)
    time.sleep(2)
    drive.motor_back(40)          
    time.sleep(2)
    drive.clean_GPIO()
