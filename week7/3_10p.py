import RPi.GPIO as GPIO
import time

# 4) 4개의 스위치 핀 번호, 클릭 횟수, 이전 상태를 리스트로 관리
sw_pins = [5, 6, 13, 19]
click_counts = [0] * len(sw_pins)
prev_gpio_states = [0] * len(sw_pins)

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

for pin in sw_pins:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

try:
    while True:
        for i, pin in enumerate(sw_pins):
            current_gpio_state = GPIO.input(pin)

            # 3) 스위치를 누르는 순간(0->1)만 감지
            if current_gpio_state == 1 and prev_gpio_states[i] == 0:
                click_counts[i] += 1
                # 1), 2) 스위치가 눌렸을 때만, 몇 번 스위치인지와 함께 "click" 출력
                print("Switch {0} click {1}".format(i+1, click_counts[i]))

            # 다음 감지를 위해 현재 상태를 이전 상태로 저장
            prev_gpio_states[i] = current_gpio_state

        time.sleep(0.1)

except KeyboardInterrupt:
    pass

finally:
    GPIO.cleanup()