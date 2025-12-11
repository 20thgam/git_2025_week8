import cv2 as cv
import cv2.dnn
import numpy as np
import threading, time
import SDcar  # 같은 폴더에 SDcar.py가 있어야 함
import sys
import serial
from tensorflow.keras.models import load_model
import RPi.GPIO as GPIO

# ==========================================
# 1. 설정 및 초기화
# ==========================================

# 블루투스 포트 설정
try:
    bleSerial = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=1.0)
except Exception as e:
    print(f"Bluetooth Serial Init Error: {e}")
    bleSerial = None

# COCO 클래스 이름 로드
class_names = []
try:
    with open('object_detection_classes_coco.txt', 'r') as f:
        class_names = f.read().split('\n')
except FileNotFoundError:
    class_names = ['background', 'person']

def id_class_name(class_id, class_names):
    return class_names[class_id] if 0 <= class_id < len(class_names) else "Unknown"

speed = 30 
epsilon = 0.0001

# GPIO 설정
LED_PIN = (20, 21)
BUZZER_PIN = 12
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN[0], GPIO.OUT)
GPIO.setup(LED_PIN[1], GPIO.OUT)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
buzzer_pwm = GPIO.PWM(BUZZER_PIN, 1000)
buzzer_pwm.start(0)

# ==========================================
# 2. 블루투스 시리얼 스레드
# ==========================================
def serial_thread():
    global is_running, enable_AIdrive, enable_objectdetection, car 
    
    print("Bluetooth Serial Thread Started")
    
    while is_running:
        if bleSerial is None:
            break
            
        try:
            if bleSerial.in_waiting > 0:
                data = bleSerial.readline()
                command = data.decode('utf-8').strip()
                
                if not command:
                    continue
                
                print(f"[BT CMD] {command}")
                
                if command == "auto":
                    enable_AIdrive = True
                    print("AI Mode ON (via BT)")
                    
                elif command == "manual":
                    enable_AIdrive = False
                    car.motor_stop()
                    print("AI Mode OFF (via BT)")

                elif command == "detect_on":
                    enable_objectdetection = True
                    print("Detection ON (via BT)")
                elif command == "detect_off":
                    enable_objectdetection = False
                    print("Detection OFF (via BT)")
                
                elif not enable_AIdrive:
                    if command == "go":
                        car.motor_go(speed)
                    elif command == "back":
                        car.motor_back(speed)
                    elif command == "left":
                        car.motor_left(20)
                    elif command == "right":
                        car.motor_right(20)
                    elif command == "stop":
                        car.motor_stop()
                        
        except Exception as e:
            print(f"BT Error: {e}")
            time.sleep(1)

# ==========================================
# 3. 객체 인식 스레드
# ==========================================
def object_detection_thread():
    global frame, enable_objectdetection, class_name, last_obstacle_time
    
    model = cv2.dnn.readNetFromTensorflow(
        model='frozen_inference_graph.pb',
        config='ssd_mobilenet_v2_coco_2018_03_29.pbtxt'
    )
    
    cnt = 0
    num_skip = 5
    size_img = 300
    
    while True:
        cnt += 1
        if enable_objectdetection is True and cnt % num_skip == 0:
            class_name = "Unknown"

            lock.acquire()
            if frame is None:
                lock.release()
                continue
            imagednn = frame.copy()
            lock.release()
            
            image_height, image_width, _ = imagednn.shape
            
            model.setInput(cv2.dnn.blobFromImage(imagednn, size=(size_img, size_img), swapRB=True))
            output = model.forward()
            
            for detection in output[0,0,:,:]:
                confidence = detection[2]
                if confidence > 0.4:
                    class_id = int(detection[1]) - 1
                    if 0 <= class_id < len(class_names):
                        found_class = class_names[class_id]
                        
                        if found_class == 'person':
                            class_name = 'person'
                            last_obstacle_time = time.time()
                        
                        box_x = int(detection[3] * image_width)
                        box_y = int(detection[4] * image_height)
                        box_width = int(detection[5] * image_width)
                        box_height = int(detection[6] * image_height)
                        cv.rectangle(imagednn, (box_x, box_y), (box_width, box_height), (0, 255, 0), thickness=2) 
                        cv.putText(imagednn, found_class, (box_x, int(box_y + 0.05 * image_height)), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            cv.imshow('Object Detection Result', imagednn)
            
        if is_running is False:
            break
        if cnt >= 1000000:
            cnt = 0

# ==========================================
# 4. 키보드 제어 함수
# ==========================================
def key_cmd(which_key):
    is_exit = False
    global enable_AIdrive, enable_objectdetection, car
    
    if which_key & 0xFF == 184: car.motor_go(speed)
    elif which_key & 0xFF == 178: car.motor_back(speed)
    elif which_key & 0xFF == 180: car.motor_left(25)
    elif which_key & 0xFF == 182: car.motor_right(25)
    elif which_key & 0xFF == 181: 
        car.motor_stop()
        enable_AIdrive = False
        
    elif which_key & 0xFF == ord('q'): 
        car.motor_stop()
        enable_AIdrive = False
        is_exit = True
        
    elif which_key & 0xFF == ord('e'): 
        enable_AIdrive = True
        print('AI Drive ON')
    elif which_key & 0xFF == ord('w'): 
        enable_AIdrive = False
        car.motor_stop()
        print('AI Drive OFF')
        
    elif which_key & 0xFF == ord('t'): 
        enable_objectdetection = True
        print('Object Detection ON')
    elif which_key & 0xFF == ord('r'): 
        enable_objectdetection = False
        print('Object Detection OFF')
        
    return is_exit

# ==========================================
# 5. AI 주행 함수 (부저 1회 울림)
# ==========================================
def drive_AI(img):
    global last_obstacle_time, car, beep_done # beep_done 전역 변수 사용
    
    # 2.0초 동안 장애물 감지 이력 있으면 정지
    if time.time() - last_obstacle_time < 3.0:
        print("Person Detected! Waiting...")
        car.motor_stop()
        
        GPIO.output(LED_PIN[0], GPIO.HIGH)
        GPIO.output(LED_PIN[1], GPIO.HIGH)
        
        # [핵심] 부저가 아직 안 울렸을 때만 울림
        if not beep_done:
            # 소리 크기 10 (조절 가능: 0~100)
            buzzer_pwm.ChangeDutyCycle(10) 
            time.sleep(0.1) # 짧게 삑!
            buzzer_pwm.ChangeDutyCycle(0) 
            beep_done = True # 울렸다고 표시
            
        return 

    # --- 사람이 없으면 (주행 모드) ---

    # 다시 주행 시작하면 부저 상태 초기화 (다음 감지 때 또 울리게)
    if beep_done:
        beep_done = False
        
    GPIO.output(LED_PIN[0], GPIO.LOW)
    GPIO.output(LED_PIN[1], GPIO.LOW)
    buzzer_pwm.ChangeDutyCycle(0)
    
    img = np.expand_dims(img, 0)
    res = model.predict(img)[0]
    steering_angle = np.argmax(np.array(res))
    
    if steering_angle == 0:
        car.motor_go(60)
    elif steering_angle == 1:
        car.motor_left(40)
    elif steering_angle == 2:
        car.motor_right(40)

# ==========================================
# 6. 메인 루프
# ==========================================
def main():
    global frame, is_running
    try:
        while (camera.isOpened()):
            lock.acquire()
            ret, frame = camera.read()
            if not ret:
                lock.release()
                break
            frame = cv.flip(frame, -1)
            lock.release()
            
            cv.imshow('camera', frame)
            
            crop_img = frame[int(v_y / 2):, :]
            crop_img = cv.resize(crop_img, (200, 66))
            
            if enable_AIdrive == True:
                drive_AI(crop_img)
            
            is_exit = False
            which_key = cv.waitKey(1)
            if which_key > 0:
                is_exit = key_cmd(which_key)
            if is_exit is True:
                break
                
    except Exception as e:
        print("Main Error:", e)
        is_running = False

if __name__ == '__main__':
    # 1. 모델 로드
    model_path = 'lane_navigation_20251126_0351.h5'
    model = load_model(model_path)
    
    # 2. 카메라 설정
    W = 320
    H = 240
    camera = cv.VideoCapture(0, cv.CAP_V4L)
    camera.set(cv.CAP_PROP_FRAME_WIDTH, W)
    camera.set(cv.CAP_PROP_FRAME_HEIGHT, H)
    camera.set(cv.CAP_PROP_FPS, 30)
    v_x = W
    v_y = H
    
    lock = threading.Lock()
    
    # 3. 전역 변수 초기화
    is_running = True
    enable_AIdrive = False
    enable_objectdetection = False
    class_name = "Unknown"
    last_obstacle_time = 0
    frame = None
    
    # [수정] 여기서 beep_done 변수를 만들어줘야 에러가 안 납니다!
    beep_done = False

    # 4. 자동차 객체 생성
    car = SDcar.Drive()

    # 5. 스레드 시작
    t_task1 = threading.Thread(target = object_detection_thread)
    t_task1.start()
    
    t_bt = threading.Thread(target = serial_thread)
    t_bt.daemon = True 
    t_bt.start()
    
    try:
        main()
    finally:
        print("Cleaning up...")
        is_running = False
        t_task1.join()
        if bleSerial:
            bleSerial.close()
        camera.release()
        cv.destroyAllWindows()
        GPIO.cleanup()
        car.clean_GPIO()
        print('Program Ended')