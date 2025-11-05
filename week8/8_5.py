import RPi.GPIO as GPIO
import threading
import serial
import time

# ==========
# GPIO 핀 설정 (L298N 모터 드라이버 기준 예시)
# 사용자의 모터 드라이버에 맞게 핀 번호를 수정해야 합니다.
# ==========
MOTOR_A_EN = 18  # 왼쪽 모터 Enable
MOTOR_A_IN1 = 22
MOTOR_A_IN2 = 27

MOTOR_B_EN = 23  # 오른쪽 모터 Enable
MOTOR_B_IN1 = 25
MOTOR_B_IN2 = 24

# ==========
# 블루투스 시리얼 설정
# ==========
bleSerial = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=1.0)

# ==========
# 전역 변수: 블루투스 데이터를 저장할 공간
# ==========
gData = ""

# ==========
# 모터 제어 함수
# ==========
def back():
    print("motor: back")
    GPIO.output(MOTOR_A_IN1, GPIO.HIGH)
    GPIO.output(MOTOR_A_IN2, GPIO.LOW)
    GPIO.output(MOTOR_B_IN1, GPIO.HIGH)
    GPIO.output(MOTOR_B_IN2, GPIO.LOW)

def go():
    print("motor: go")
    GPIO.output(MOTOR_A_IN1, GPIO.LOW)
    GPIO.output(MOTOR_A_IN2, GPIO.HIGH)
    GPIO.output(MOTOR_B_IN1, GPIO.LOW)
    GPIO.output(MOTOR_B_IN2, GPIO.HIGH)

def right():
    print("motor: right")
    GPIO.output(MOTOR_A_IN1, GPIO.LOW)
    GPIO.output(MOTOR_A_IN2, GPIO.HIGH)
    GPIO.output(MOTOR_B_IN1, GPIO.HIGH)
    GPIO.output(MOTOR_B_IN2, GPIO.LOW)

def left():
    print("motor: left")
    GPIO.output(MOTOR_A_IN1, GPIO.HIGH)
    GPIO.output(MOTOR_A_IN2, GPIO.LOW)
    GPIO.output(MOTOR_B_IN1, GPIO.LOW)
    GPIO.output(MOTOR_B_IN2, GPIO.HIGH)

def stop():
    print("motor: stop")
    GPIO.output(MOTOR_A_IN1, GPIO.LOW)
    GPIO.output(MOTOR_A_IN2, GPIO.LOW)
    GPIO.output(MOTOR_B_IN1, GPIO.LOW)
    GPIO.output(MOTOR_B_IN2, GPIO.LOW)

# ==========
# 블루투스 통신을 처리하는 쓰레드 함수
# ==========
def serial_thread():
    global gData
    while True:
        # 블루투스로부터 데이터 한 줄을 읽어옴
        data = bleSerial.readline()
        # byte 형태의 데이터를 문자열(string)으로 변환
        data = data.decode('utf-8').strip()
        
        # 데이터가 있는 경우에만 gData에 저장
        if data:
            print(f"Received from BT: {data}")
            gData = data

# ==========
# 메인 로직 함수: gData 값을 확인하고 자동차를 제어
# ==========
def main():
    global gData
    try:
        while True:
            if "go" in gData:
                gData = ""  # 명령을 처리했으므로 변수 초기화
                go()
            elif "back" in gData:
                gData = ""
                back()
            elif "left" in gData:
                gData = ""
                left()
            elif "right" in gData:
                gData = ""
                right()
            elif "stop" in gData:
                gData = ""
                stop()
            
            time.sleep(0.1) # CPU 사용량을 줄이기 위해 잠시 대기

    except KeyboardInterrupt:
        pass

# ==========
# 프로그램 시작점
# ==========
if __name__ == '__main__':
    # GPIO 설정
    GPIO.setmode(GPIO.BCM)
    GPIO.setup([MOTOR_A_EN, MOTOR_A_IN1, MOTOR_A_IN2, MOTOR_B_EN, MOTOR_B_IN1, MOTOR_B_IN2], GPIO.OUT)
    # 모터 Enable 핀 활성화
    GPIO.output(MOTOR_A_EN, GPIO.HIGH)
    GPIO.output(MOTOR_B_EN, GPIO.HIGH)
    
    # 블루투스 통신 쓰레드 생성 및 시작
    task1 = threading.Thread(target=serial_thread)
    task1.start()

    print("Bluetooth Car Control Start!")
    
    # 메인 함수 실행
    main()
    
    # 프로그램 종료 시 정리
    bleSerial.close()
    GPIO.cleanup()
    print("Program exit.")