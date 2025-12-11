import cv2 as cv
import cv2.dnn
import numpy as np
import threading, time
import SDcar
import sys
import tensorflow as tf
from tensorflow.keras.models import load_model
import RPi.GPIO as GPIO

# ==========================================
# 1. 설정 및 초기화
# ==========================================

# COCO 클래스 이름 로드 (파일이 없을 경우 대비 예외처리)
class_names = []
try:
    with open('object_detection_classes_coco.txt', 'r') as f:
        class_names = f.read().split('\n')
except FileNotFoundError:
    class_names = ['background', 'person'] # 기본값

COLORS = np.random.uniform(0, 255, size=(len(class_names), 3))

def id_class_name(class_id, class_names):
    return class_names[class_id] if 0 <= class_id < len(class_names) else "Unknown"

speed = 100
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
# 2. 객체 인식 스레드 (Object Detection)
# ==========================================
def object_detection_thread():
    global frame, enable_objectdetection, class_name, last_obstacle_time
    
    # 모델 로드
    model = cv2.dnn.readNetFromTensorflow(
        model='frozen_inference_graph.pb',
        config='ssd_mobilenet_v2_coco_2018_03_29.pbtxt'
    )
    
    cnt = 0
    num_skip = 5 # 반응 속도를 위해 5프레임마다 분석 (조절 가능)
    size_img = 300
    
    while True:
        cnt += 1
        if enable_objectdetection is True and cnt % num_skip == 0:
            
            # [중요] 매 루프마다 초기화 (사람이 사라짐을 감지하기 위함)
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
                        
                        # [핵심] 사람(person)이 감지되면 현재 시간을 기록
                        if found_class == 'person':
                            class_name = 'person'
                            last_obstacle_time = time.time()
                        
                        # 박스 그리기
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
# 3. 키보드 제어 함수
# ==========================================
def key_cmd(which_key):
    is_exit = False
    global enable_AIdrive
    global enable_objectdetection
    
    if which_key & 0xFF == 184: # Up
        car.motor_go(speed)
    elif which_key & 0xFF == 178: # Down
        car.motor_back(speed)
    elif which_key & 0xFF == 180: # Left
        car.motor_left(25)
    elif which_key & 0xFF == 182: # Right
        car.motor_right(25)
    elif which_key & 0xFF == 181: # Stop (Center)
        car.motor_stop()
        enable_AIdrive = False
        print('Manual Stop')
        
    elif which_key & 0xFF == ord('q'): # Quit
        car.motor_stop()
        print('Exit Program')
        enable_AIdrive = False
        is_exit = True
        
    elif which_key & 0xFF == ord('e'): # AI On
        enable_AIdrive = True
        print('AI Drive ON')
    elif which_key & 0xFF == ord('w'): # AI Off
        enable_AIdrive = False
        car.motor_stop()
        print('AI Drive OFF')
        
    elif which_key & 0xFF == ord('t'): # Detect On
        enable_objectdetection = True
        print('Object Detection ON')
    elif which_key & 0xFF == ord('r'): # Detect Off
        enable_objectdetection = False
        print('Object Detection OFF')
        
    return is_exit

# ==========================================
# 4. AI 주행 판단 함수 (Time Buffer 적용)
# ==========================================
def drive_AI(img):
    global last_obstacle_time
    
    # [핵심 로직] 마지막으로 사람을 본 지 1.0초가 안 지났으면 멈춤
    # (사람이 화면에 있으면 시간 차이는 0.1초 미만이므로 계속 멈춤)
    # (사람이 사라져도 1초 동안은 대기 후 출발)
    if time.time() - last_obstacle_time < 3.0:
        print("Person Detected! Waiting...")
        car.motor_stop()
        
        # 경고음 및 LED (Non-blocking 방식: 짧게 동작하고 리턴)
        GPIO.output(LED_PIN[0], GPIO.HIGH)
        GPIO.output(LED_PIN[1], GPIO.HIGH)
        buzzer_pwm.ChangeDutyCycle(50)
        time.sleep(0.1) # 화면 끊김 방지를 위해 아주 짧게
        
        GPIO.output(LED_PIN[0], GPIO.LOW)
        GPIO.output(LED_PIN[1], GPIO.LOW)
        buzzer_pwm.ChangeDutyCycle(0)
        
        return # 주행 코드로 내려가지 않고 함수 종료

    # --- 사람이 없으면 (1초 이상 경과 시) 아래 실행 ---
    
    # 평상시 LED/부저 끄기
    GPIO.output(LED_PIN[0], GPIO.LOW)
    GPIO.output(LED_PIN[1], GPIO.LOW)
    buzzer_pwm.ChangeDutyCycle(0)
    
    # 차선 인식 주행
    img = np.expand_dims(img, 0)
    res = model.predict(img)[0]
    steering_angle = np.argmax(np.array(res))
    
    if steering_angle == 0:
        # print("Go")
        car.motor_go(40)
    elif steering_angle == 1:
        # print("Left")
        car.motor_left(20)
    elif steering_angle == 2:
        # print("Right")
        car.motor_right(20)

# ==========================================
# 5. 메인 함수
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
            
            # AI 주행용 이미지 전처리
            crop_img = frame[int(v_y / 2):, :]
            crop_img = cv.resize(crop_img, (200, 66))
            # cv.imshow('crop_img', crop_img) 
            
            if enable_AIdrive == True:
                drive_AI(crop_img)
            
            is_exit = False
            which_key = cv.waitKey(1)
            if which_key > 0:
                is_exit = key_cmd(which_key)
            if is_exit is True:
                break
                
    except Exception as e:
        exception_type, exception_object, exception_traceback = sys.exc_info()
        filename = exception_traceback.tb_frame.f_code.co_filename
        line_number = exception_traceback.tb_lineno
        print("Exception type: ", exception_type)
        print("File name: ", filename)
        print("Line number: ", line_number)
        is_running = False

# ==========================================
# 6. 프로그램 시작점
# ==========================================
if __name__ == '__main__':
    # 모델 로드 (주행용)
    model_path = 'lane_navigation_20251126_0351.h5'
    model = load_model(model_path)
    
    # 카메라 설정
    W = 320
    H = 240
    camera = cv.VideoCapture(0, cv.CAP_V4L)
    camera.set(cv.CAP_PROP_FRAME_WIDTH, W)
    camera.set(cv.CAP_PROP_FRAME_HEIGHT, H)
    camera.set(cv.CAP_PROP_FPS, 30)
    
    v_x = W
    v_y = H
    
    lock = threading.Lock()
    
    # [중요] 전역 변수 초기화
    is_running = True
    enable_AIdrive = False
    enable_objectdetection = False
    class_name = "Unknown"
    last_obstacle_time = 0  # 초기 시간 0
    frame = None

    # 객체 인식 스레드 시작
    t_task1 = threading.Thread(target = object_detection_thread)
    t_task1.start()
    
    # 모터 제어 객체
    car = SDcar.Drive()
    
    try:
        main()
    finally:
        print("Cleaning up...")
        is_running = False
        t_task1.join()
        camera.release()
        cv.destroyAllWindows()
        GPIO.cleanup()
        car.clean_GPIO()
        print('Program Ended')