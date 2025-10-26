import RPi.GPIO as GPIO
import time

# --- 핀 번호 설정 ---
# 모터 A (왼쪽)
PWMA = 18; AIN1 = 22; AIN2 = 27
# 모터 B (오른쪽)
PWMB = 23; BIN1 = 25; BIN2 = 24
# 스위치
SW1, SW2, SW3, SW4 = 5, 6, 13, 19

# --- GPIO 설정 ---
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
motor_pins = [PWMA, AIN1, AIN2, PWMB, BIN1, BIN2]
for pin in motor_pins:
    GPIO.setup(pin, GPIO.OUT)
switch_pins = [SW1, SW2, SW3, SW4]
for pin in switch_pins:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# --- PWM 객체 생성 ---
L_Motor = GPIO.PWM(PWMA, 500)
L_Motor.start(0)
R_Motor = GPIO.PWM(PWMB, 500)
R_Motor.start(0)

# --- 모터 제어 함수 ---
def move_forward(speed=50):
    GPIO.output(AIN1, 0); GPIO.output(AIN2, 1)
    GPIO.output(BIN1, 0); GPIO.output(BIN2, 1)
    L_Motor.ChangeDutyCycle(speed)
    R_Motor.ChangeDutyCycle(speed)

def move_backward(speed=50):
    GPIO.output(AIN1, 1); GPIO.output(AIN2, 0)
    GPIO.output(BIN1, 1); GPIO.output(BIN2, 0)
    L_Motor.ChangeDutyCycle(speed)
    R_Motor.ChangeDutyCycle(speed)

def turn_left(speed=50):
    GPIO.output(AIN1, 1); GPIO.output(AIN2, 0)
    GPIO.output(BIN1, 0); GPIO.output(BIN2, 1)
    L_Motor.ChangeDutyCycle(speed)
    R_Motor.ChangeDutyCycle(speed)

def turn_right(speed=50):
    GPIO.output(AIN1, 0); GPIO.output(AIN2, 1)
    GPIO.output(BIN1, 1); GPIO.output(BIN2, 0)
    L_Motor.ChangeDutyCycle(speed)
    R_Motor.ChangeDutyCycle(speed)

def stop():
    L_Motor.ChangeDutyCycle(0)
    R_Motor.ChangeDutyCycle(0)

# --- 메인 코드 ---
try:
    # --- 상태 관리 변수 ---
    patrol_active = True  # True일 때만 자율 주행 활성화
    last_patrol_time = time.time()
    patrol_is_moving = False

    while True:
        # 4개의 스위치 상태를 한 번에 읽기
        sw1_state = GPIO.input(SW1)
        sw2_state = GPIO.input(SW2)
        sw3_state = GPIO.input(SW3)
        sw4_state = GPIO.input(SW4)

        # 1. 버튼이 하나라도 눌렸는지 확인
        if sw1_state or sw2_state or sw3_state or sw4_state:
            # 버튼이 눌리는 순간, 자율 주행 모드를 영구적으로 비활성화
            if patrol_active:
                print("\nManual")
                patrol_active = False

            # 눌린 버튼에 따라 수동 조작 실행
            if sw1_state:
                print("SW1: For")
                move_forward()
            elif sw2_state:
                print("SW2: Rgt")
                turn_right()
            elif sw3_state:
                print("SW3: Lft")
                turn_left()
            elif sw4_state:
                print("SW4: Bck")
                move_backward()
        
        # 2. 아무 버튼도 눌리지 않았을 경우
        else:
            # (1) 아직 자율 주행 모드일 때 -> 전진/정지 반복
            if patrol_active:
                if time.time() - last_patrol_time > 1.0:
                    patrol_is_moving = not patrol_is_moving
                    last_patrol_time = time.time()
                    if patrol_is_moving:
                        print("Auto: For")
                        move_forward(100)
                    else:
                        print("Auto: Stp")
                        stop()
            # (2) 수동 조작 후 버튼에서 손을 뗀 상태 -> 그냥 정지
            else:
                stop()

        time.sleep(0.02)

except KeyboardInterrupt:
    pass

finally:
    GPIO.cleanup()