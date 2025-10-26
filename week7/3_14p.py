import RPi.GPIO as GPIO
import time

# 사용할 핀 번호 설정
BUZZER = 12
sw_pins = [5, 6, 13, 19]

# '도레미파솔라시도' 음계 주파수 리스트
scale = [261, 294, 329, 349, 392, 440, 493, 523]

# 각 스위치 핀에 '도, 레, 미, 파' 음을 할당 (Dictionary 자료형 사용)
note_map = {
    sw_pins[0]: scale[5]/2,  # 5번핀: 라
    sw_pins[1]: scale[2],  # 6번핀: 미
    sw_pins[2]: scale[0],  # 13번핀: 도
    sw_pins[3]: scale[6]/2   # 19번핀: 시
}

# GPIO 설정
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUZZER, GPIO.OUT)
for pin in sw_pins:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# PWM 객체 생성 (초기 주파수 100Hz)
p = GPIO.PWM(BUZZER, 100)

try:
    # 1. 프로그램 시작 시 '도레미파솔라시도' 연주
    p.start(50)  # Duty Cycle 50%로 PWM 시작
    for freq in scale:
        p.ChangeFrequency(freq)
        print("현재 주파수: {0}Hz".format(freq))
        time.sleep(0.5)
    p.stop()  # 연주가 끝나면 PWM 정지
    print("버튼을 눌러 연주하세요. (종료: Ctrl+C)")

    # 2. 버튼 입력을 기다리는 무한 루프
    while True:
        pressed_pin = None
        # 모든 스위치 핀을 확인하여 눌린 버튼이 있는지 찾음
        for pin in sw_pins:
            if GPIO.input(pin) == 1:
                pressed_pin = pin
                break # 버튼 하나가 눌리면 더 이상 찾지 않음

        if pressed_pin is not None:
            # 3. 버튼이 눌렸으면 해당 음으로 주파수 변경 후 소리 재생
            freq = note_map[pressed_pin]
            p.ChangeFrequency(freq)
            p.start(50)
            print("눌린 버튼: GPIO {0}, 주파수: {1}Hz".format(pressed_pin, freq))
        else:
            # 4. 아무 버튼도 눌리지 않았으면 소리 정지
            p.stop()

        time.sleep(0.1) # CPU 부하를 줄이기 위한 짧은 대기


except KeyboardInterrupt:
    pass

finally:
    p.stop()
    GPIO.cleanup()