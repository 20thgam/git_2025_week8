import cv2 as cv
import numpy as np
import threading, time
import SDcar 
import sys
import os
import datetime
import RPi.GPIO as GPIO

# --- 전역 변수 설정 ---
speed = 70       # 직진 속도
speed_rot = 40   # 회전 속도
epsilon = 0.0001 # 0 나누기 방지
is_running = True
enable_linetracing = False 

# --- 부저 핀 설정 (원하는 핀번호로 수정 가능) ---
BUZZER_PIN = 4 

# --- 스레드 함수 (생존 신고) ---
def func_thread():
    i = 0
    while True:
        # print("alive!!")    
        time.sleep(1)
        i = i+1
        if is_running is False:
            break

# --- 부저 울리기 함수 ---
def beep(duration=0.1, count=1):
    for _ in range(count):
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        time.sleep(0.1)

# --- 이미지 저장 함수 ---
def save_img(frame, angle):
    global filecnt
    filename = 'train_{0:05d}_{1:03d}.png'.format(filecnt, angle)
    filename = os.path.join(filepath, filename)
    
    cv.imwrite(filename, frame)
    print(f'Saved: {filename} (Cnt: {filecnt})')
    filecnt += 1

# --- 키보드 명령 처리 ---
def key_cmd(which_key):
    global enable_linetracing
    is_exit = False
    
    if which_key & 0xFF == ord('q'):  # 종료
        car.motor_stop()
        print('exit')        
        is_exit = True
    elif which_key & 0xFF == ord('e'): # 자율주행 및 수집 시작/재개
        enable_linetracing = True
        print('Auto Collection STARTED / RESUMED')
    elif which_key & 0xFF == ord('w'): # 일시 정지
        enable_linetracing = False
        car.motor_stop()
        print('Auto Collection PAUSED')
        
    return is_exit  

# --- 노란색 마스크 검출 (HSV) ---
def detect_maskY_HSV(frame):
    crop_hsv = cv.cvtColor(frame, cv.COLOR_BGR2HSV)
    # 노란색 범위 (환경에 따라 튜닝 필요)
    lower_Y = np.array([25, 50, 100])
    upper_Y = np.array([35, 255, 255])
    mask_Y = cv.inRange(crop_hsv, lower_Y, upper_Y)
    return mask_Y

# --- 자율 주행 로직 및 방향 결정 ---
def get_steering_command(cx, v_x_grid):
    if v_x_grid[2] <= cx < v_x_grid[3]: 
        return 0 # 직진
    elif cx < v_x_grid[2]: 
        return 1 # 좌회전
    elif cx >= v_x_grid[3]: 
        return 2 # 우회전
    return 0

# --- 메인 함수 ---
# --- 메인 함수 수정본 ---
def main():
    global enable_linetracing, is_running, filecnt
    
    camera = cv.VideoCapture(0)
    camera.set(cv.CAP_PROP_FRAME_WIDTH, v_x) 
    camera.set(cv.CAP_PROP_FRAME_HEIGHT, v_y)
    
    prev_label = -1 
    
    # [추가] 라인을 놓친 횟수를 세는 변수
    no_line_cnt = 0 
    # [추가] 최대 몇 프레임까지 눈감고 직진할지 설정 (20프레임 ≈ 1~2초)
    MAX_BLIND_FRAMES = 70 

    try:
        while(camera.isOpened()):
            ret, frame = camera.read()
            if not ret:
                break

            frame = cv.flip(frame, -1)
            
            # 이미지 전처리
            model_img = frame[int(v_y/2):, :]
            model_img = cv.resize(model_img, (200, 66))
            
            drive_img = frame[180:, :]
            maskY = detect_maskY_HSV(drive_img)
            contours, _ = cv.findContours(maskY, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)

            display_img = model_img.copy()

            if enable_linetracing:
                # ---------------------------------------------------------
                # CASE 1: 라인을 찾았을 때 (정상 주행)
                # ---------------------------------------------------------
                if len(contours) > 0:
                    no_line_cnt = 0 # 카운터 리셋
                    
                    c = max(contours, key=cv.contourArea)
                    m = cv.moments(c)
                    
                    if m['m00'] > 0:
                        cx = int(m['m10'] / (m['m00'] + epsilon))
                        
                        moment[0] = moment[1]
                        moment[1] = moment[2]
                        moment[2] = cx
                        avg_cx = np.mean(moment)

                        label = get_steering_command(avg_cx, v_x_grid)
                        
                        if label == 0:
                            car.motor_go(speed)
                        elif label == 1:
                            car.motor_left(speed_rot)
                        elif label == 2:
                            car.motor_right(speed_rot)
                        
                        if label != prev_label:
                            save_img(model_img, label)
                            prev_label = label
                            
                            # 550장/1100장 체크 로직 (기존과 동일)
                            if filecnt == 550:
                                car.motor_stop()
                                enable_linetracing = False
                                print("\n=== 550 PAUSED ===\n")
                                beep(0.5, 1)
                            elif filecnt >= 1100:
                                car.motor_stop()
                                enable_linetracing = False
                                print("\n=== 1100 FINISHED ===\n")
                                beep(0.2, 2)
                                is_running = False
                                break

                # ---------------------------------------------------------
                # CASE 2: 라인을 놓쳤을 때 (횡단보도 등)
                # ---------------------------------------------------------
                else:
                    no_line_cnt += 1 # 카운터 증가

                    # 아직 허용 범위 내라면 -> "직진" (Blind Run)
                    if no_line_cnt < MAX_BLIND_FRAMES:
                        print(f"Line Lost! Blind Run.. ({no_line_cnt}/{MAX_BLIND_FRAMES})")
                        
                        car.motor_go(speed) # 강제 직진
                        label = 0 # 라벨은 '직진'으로 저장
                        
                        # 횡단보도에서도 데이터가 필요하면 저장 (조향 변경 시)
                        if label != prev_label:
                            save_img(model_img, label)
                            prev_label = label

                    # 너무 오랫동안 안 보이면 -> "정지"
                    else:
                        car.motor_stop()
                        print("Line Lost completely - STOP")

            cv.imshow('Smart Collector', display_img)

            is_exit = False
            which_key = cv.waitKey(20)
            if which_key > 0:
                is_exit = key_cmd(which_key)    
            
            if is_exit is True:
                cv.destroyAllWindows()
                break

    except Exception as e:
        print("Exception:", e)
        is_running = False
    finally:
        camera.release()

if __name__ == '__main__':
    # GPIO 설정 (부저용)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUZZER_PIN, GPIO.OUT)
    GPIO.output(BUZZER_PIN, GPIO.LOW)

    v_x = 320
    v_y = 240
    v_x_grid = [int(v_x*i/10) for i in range(1, 10)]
    moment = np.array([0, 0, 0])

    # 저장 경로 설정
    parent_dir = "dataset"
    if not os.path.isdir(parent_dir):
        os.mkdir(parent_dir)
    save_dir = datetime.datetime.now().strftime('%Y%m%d_%H%M')
    filepath = os.path.join(parent_dir, save_dir)
    if not os.path.isdir(filepath):
        os.mkdir(filepath)
    print(f'Save Directory: {filepath}')

    filecnt = 0
    
    t_task1 = threading.Thread(target = func_thread)
    t_task1.start()

    car = SDcar.Drive()
    
    is_running = True
    main() 
    
    is_running = False
    car.clean_GPIO()
    GPIO.cleanup() # 부저 핀 정리