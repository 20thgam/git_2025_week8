import cv2 as cv
import cv2.dnn
import numpy as np
import threading, time
import SDcar
import sys
import tensorflow as tf
from tensorflow.keras.models import load_model
import RPi.GPIO as GPIO

class_names = []
with open('object_detection_classes_coco.txt', 'r') as f:
    class_names = f.read().split('\n')

COLORS = np.random.uniform(0, 255, size=(len(class_names), 3))

def id_class_name(class_id, class_names):
    return class_names[class_id] if 0 <= class_id < len(class_names) else "Unknown"

speed = 30
epsilon = 0.0001

def object_detection_thread():
    global frame, enable_objectdetection, class_name
    model = cv2.dnn.readNetFromTensorflow(
        model='frozen_inference_graph.pb',
        config='ssd_mobilenet_v2_coco_2018_03_29.pbtxt'
    )
    cnt = 0
    num_skip = 10
    size_img = 300
    while True:
        cnt += 1
        if enable_objectdetection is True and cnt % num_skip == 0:
            print('cnt', cnt)
            lock.acquire()
            if frame is None:
                lock.release()
                continue
            imagednn = frame.copy()
            lock.release()
            image_height, image_width, _ = imagednn.shape
            
            starttime = time.time()
            model.setInput(cv2.dnn.blobFromImage(imagednn, size=(size_img, size_img), swapRB=True))
            output = model.forward()
            print('objection detection result: ', output[0,0,:,:].shape)
            
            for detection in output[0,0,:,:]:
                confidence = detection[2]
                if confidence > 0.4:
                    class_id = int(detection[1]) - 1
                    class_name = id_class_name(class_id, class_names)
                    print(f"{class_id} {detection[2]} {class_name}")
                    if class_id < len(class_names):
                        class_name = class_names[class_id]
                        color = COLORS[class_id]
                    box_x = detection[3] * image_width
                    box_y = detection[4] * image_height
                    box_width = detection[5] * image_width
                    box_height = detection[6] * image_height
                    cv.rectangle(imagednn, (int(box_x), int(box_y)), (int(box_width), int(box_height)), (0, 255, 0), thickness=2) 
                    cv.putText(imagednn, class_name, (int(box_x), int(box_y + 0.05 * image_height)), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    
            elapsed = time.time() - starttime
            print("object detection, elapsed : {0:0.4f}, fps : {1:0.4f}".format(elapsed, 1/elapsed))
            cv.imshow('Object Detection Result', imagednn)
            
        if is_running is False:
            break
        if cnt >= 1000000:
            cnt = 0

def key_cmd(which_key):
    print('which_key', which_key)
    is_exit = False
    global enable_AIdrive
    global enable_objectdetection
    if which_key & 0xFF == 184:
        print('up')
        car.motor_go(speed)
    elif which_key & 0xFF == 178:
        print('down')
        car.motor_back(speed)
    elif which_key & 0xFF == 180:
        print('left')
        car.motor_left(25)
    elif which_key & 0xFF == 182:
        print('right')
        car.motor_right(25)
    elif which_key & 0xFF == 181:
        car.motor_stop()
        enable_AIdrive = False
        print('stop')
    elif which_key & 0xFF == ord('q'):
        car.motor_stop()
        print('exit')
        enable_AIdrive = False
        is_exit = True
        print('enable_AIdrive: ', enable_AIdrive)
    elif which_key & 0xFF == ord('e'):
        enable_AIdrive = True
        print('enable_AIdrive: ', enable_AIdrive)
    elif which_key & 0xFF == ord('w'):
        enable_AIdrive = False
        car.motor_stop()
        print('enable_AIdrive 2: ', enable_AIdrive)
    elif which_key & 0xFF == ord('t'):
        enable_objectdetection = True
        print('enable_objectdetection: ', enable_objectdetection)
    elif which_key & 0xFF == ord('r'):
        enable_objectdetection = False
        print('enable_objectdetection: ', enable_objectdetection)
    return is_exit

LED_PIN = (20, 21)
BUZZER_PIN = 12
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN[0], GPIO.OUT)
GPIO.setup(LED_PIN[1], GPIO.OUT)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
buzzer_pwm = GPIO.PWM(BUZZER_PIN, 1000)
buzzer_pwm.start(0)

def drive_AI(img):
    global class_name
    img = np.expand_dims(img, 0)
    res = model.predict(img)[0]
    steering_angle = np.argmax(np.array(res))
    print('steering_angle', steering_angle)
    if class_name == 'person':
        print("stop for mouse detected")
        car.motor_stop()
        while True:  # [문제점] 여기서 무한루프를 돌면 카메라 화면이 멈춤
            GPIO.output(LED_PIN, GPIO.HIGH)
            buzzer_pwm.ChangeDutyCycle(50)
            time.sleep(1.0)
            GPIO.output(LED_PIN, GPIO.LOW)
            buzzer_pwm.ChangeDutyCycle(0)
            time.sleep(1.0)
            break
    elif steering_angle == 0:
        print("go")
        speedSet = 40
        car.motor_go(speedSet)
    elif steering_angle == 1:
        print("left")
        speedSet = 20
        car.motor_left(speedSet)
    elif steering_angle == 2:
        print("right")
        speedSet = 20
        car.motor_right(speedSet)
    else:
        print("This cannot be entered")

def main():
    global frame
    try:
        while (camera.isOpened()):
            starttime = time.time()
            lock.acquire()
            ret, frame = camera.read()
            frame = cv.flip(frame, -1)
            lock.release()
            cv.imshow('camera', frame)
            crop_img = frame[int(v_y / 2):, :]
            crop_img = cv.resize(crop_img, (200, 66))
            cv.imshow('crop_img ', cv.resize(crop_img, dsize=(0, 0), fx=2, fy=2))
            if enable_AIdrive == True:
                starttime = time.time()
                drive_AI(crop_img)
                elapsed = time.time() - starttime
            is_exit = False
            which_key = cv.waitKey(1)
            if which_key > 0:
                is_exit = key_cmd(which_key)
            if is_exit is True:
                cv.destroyAllWindows()
                break
    except Exception as e:
        exception_type, exception_object, exception_traceback = sys.exc_info()
        filename = exception_traceback.tb_frame.f_code.co_filename
        line_number = exception_traceback.tb_lineno
        print("Exception type: ", exception_type)
        print("File name: ", filename)
        print("Line number: ", line_number)
        global is_running
        is_running = False

if __name__ == '__main__':
    model_path = 'lane_navigation_20251126_0351.h5'
    model = load_model(model_path)
    # [문제점] 모델 중복 로드
    model_obj = cv.dnn.readNet('frozen_inference_graph.pb', 'ssd_mobilenet_v2_coco_2018_03_29.pbtxt')
    W=320
    H=240
    camera = cv.VideoCapture(0, cv.CAP_V4L)
    camera.set(cv.CAP_PROP_FRAME_WIDTH, W)
    camera.set(cv.CAP_PROP_FRAME_HEIGHT, H)
    camera.set(cv.CAP_PROP_FPS, 30)
    v_x = W
    v_y = H
    v_x_grid = [int(v_x*i/10) for i in range(1, 10)]
    print(v_x_grid)
    moment = np.array([0,0,0])
    _, frame = camera.read()
    lock = threading.Lock()
    t_task1 = threading.Thread(target = object_detection_thread)
    t_task1.start()
    car = SDcar.Drive()
    is_running = True
    enable_AIdrive = False
    enable_objectdetection = False
    class_name = -1
    
    try:
        main()
    finally:
        is_running = False
        t_task1.join()
        camera.release()
        cv.destroyAllWindows()
        GPIO.cleanup()
        car.clean_GPIO()
        print('end vis')