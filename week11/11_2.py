# drive_line_tracer.py (오류 수정본)

import cv2 as cv
import numpy as np
import threading, time
import SDcar # SDcar.py 모듈 임포트
import sys

# 전역 변수 설정
speed = 30 # 모터 속도
epsilon = 0.0001 # 0으로 나누기 방지용

# 1초마다 "alive!!" 출력 (프로그램 동작 확인용)
def func_thread():
    i = 0
    while True:
        print("alive!!")
        time.sleep(1)
        i = i+1
        if is_running is False: # 메인 프로그램 종료 시 스레드 종료
            break

# 키보드 입력 처리 함수
def key_cmd(which_key):
    print('which_key', which_key)
    is_exit = False
    global enable_linetracing # 전역 변수 사용 선언

    if which_key & 0xFF == 184: # 숫자패드 8: 전진
        print('up')
        car.motor_go(speed)
    elif which_key & 0xFF == 178: # 숫자패드 2: 후진
        print('down')
        car.motor_back(speed)
    elif which_key & 0xFF == 180: # 숫자패드 4: 좌회전
        print('left')
        car.motor_left(speed)
    elif which_key & 0xFF == 182: # 숫자패드 6: 우회전
        print('right')
        car.motor_right(speed)
    elif which_key & 0xFF == 181: # 숫자패드 5: 정지
        car.motor_stop()
        print('stop')
    elif which_key & 0xFF == ord('q'): # 'q' 키: 종료
        car.motor_stop()
        print('exit')
        is_exit = True
    elif which_key & 0xFF == ord('e'): # 'e' 키: 자율주행 시작
        enable_linetracing = True
        print('enable_linetracing:', enable_linetracing)
    elif which_key & 0xFF == ord('w'): # 'w' 키: 자율주행 중지
        enable_linetracing = False
        car.motor_stop()
        print('enable_linetracing:', enable_linetracing)
        
    return is_exit

# HSV로 노란색 마스크 검출
def detect_maskY_HSV(frame):
    # BGR -> HSV 색 공간으로 변환
    crop_hsv = cv.cvtColor(frame, cv.COLOR_BGR2HSV)
    
    # 노란색 범위 정의 (H: 25~35, S: 50~255, V: 100~255)
    # 참고: 이 값은 조명 환경에 따라 튜닝이 필요합니다.
    lower_Y = np.array([20, 40, 80])
    upper_Y = np.array([35, 255, 255])
    
    # cv.inRange 함수로 마스크 생성
    mask_Y = cv.inRange(crop_hsv, lower_Y, upper_Y)
    return mask_Y

# 라인 트레이싱 로직
def line_tracing(cx):
    global moment, v_x
    
    tolerance = 0.1 # 허용 오차 (화면 가로의 10%)
    diff = 0

    # moment 버퍼에 값이 3개 채워졌는지 확인 (최초 3프레임 스킵)
    if moment[0] != 0 and moment[1] != 0 and moment[2] != 0:
        # 3개 moment의 평균과 현재 cx의 차이(비율) 계산
        avg_m = np.mean(moment)
        diff = np.abs(avg_m - cx) / v_x
        # print('diff :.4f '.format(diff))

    # 차이가 허용 오차 이내일 경우 (정상 주행)
    if diff <= tolerance:
        # moment 버퍼 업데이트
        moment[0] = moment[1]
        moment[1] = moment[2]
        moment[2] = cx

        # cx 값(라인 중심)이 어느 그리드에 있는지에 따라 조향
        if v_x_grid[2] <= cx < v_x_grid[3]: # 중앙 그리드(3, 4번째 줄 사이)
            car.motor_go(speed)
            # print('go')
        elif cx < v_x_grid[2]: # 중앙보다 왼쪽 (v_x_grid[2] = 96)
            car.motor_left(speed)
            # print('turn left')
        elif cx >= v_x_grid[3]: # 중앙보다 오른쪽 (v_x_grid[3] = 128)
            car.motor_right(speed)
            # print('turn right')
            
    else: # 차이가 허용 오차를 넘어가면 (라인을 놓침)
        car.motor_go(speed) # 일단 직진
        print('go (diff over)')
        moment = np.array([0, 0, 0]) # moment 버퍼 초기화

# 화면에 격자 그리기
def show_grid(img):
    h, _, _ = img.shape
    for x in v_x_grid: # v_x_grid 리스트의 x좌표마다 세로줄 그리기
        cv.line(img, (x, 0), (x, h), (0,255,0), 1, cv.LINE_4)

# 메인 함수
def main():
    camera = cv.VideoCapture(0) # 카메라 열기
    camera.set(cv.CAP_PROP_FRAME_WIDTH, v_x) # 해상도 설정
    camera.set(cv.CAP_PROP_FRAME_HEIGHT, v_y)
    
    try:
        while(camera.isOpened()):
            ret, frame = camera.read() # 프레임 읽기
            if not ret:
                break
            
            frame = cv.flip(frame, -1) # 상하 반전
            
            # --- 영상 처리 시작 ---
            
            # 1. 영상 자르기 (아래쪽 180픽셀부터)
            crop_img = frame[180:, :]
            
            # 2. 노란색 라인 검출
            maskY = detect_maskY_HSV(crop_img)
            
            # 3. Contours 찾기
            contours, _ = cv.findContours(maskY, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)

            if len(contours) > 0: # Contour를 찾았으면
                # 4. 가장 큰 Contour 찾기
                c = max(contours, key=cv.contourArea)
                
                # 5. Moment 및 중심점(cx, cy) 계산
                m = cv.moments(c)
                
                # 0으로 나누기 방지 (epsilon 사용)
                cx = int(m['m10'] / (m['m00'] + epsilon))
                cy = int(m['m01'] / (m['m00'] + epsilon))

                # 6. 시각화: 중심점에 빨간 원, 윤곽선 그리기
                cv.circle(crop_img, (cx,cy), 3, (0,0,255),-1) # 중심점
                cv.drawContours(crop_img, [c], -1, (0,255,0), 2) # 윤곽선
                
                # 7. 라인 트레이싱 함수 호출 (활성화된 경우)
                if enable_linetracing == True:
                    line_tracing(cx)

            # --- 영상 처리 끝 ---

            show_grid(crop_img) # 격자 표시
            
            # 결과 화면 출력 (2배 확대)
            cv.imshow('crop_img', cv.resize(crop_img, dsize=(0,0), fx=2, fy=2))

            # 키 입력 대기 및 처리
            is_exit = False
            which_key = cv.waitKey(20)
            if which_key > 0:
                is_exit = key_cmd(which_key)
            
            if is_exit is True: # 'q' 입력 시 루프 탈출
                cv.destroyAllWindows()
                break
                
    except Exception as e:
        print(e) # 오류 발생 시 여기에서 출력됨
    finally:
        # 프로그램 종료 시 정리
        camera.release()
        global is_running
        is_running = False # 스레드 종료 신호
        
# 이 파일이 메인으로 실행될 때
if __name__ == '__main__':
    v_x = 320 # 카메라 가로 해상도
    v_y = 240 # 카메라 세로 해상도
    
    # 격자선 x좌표 리스트 (화면 10등분)
    v_x_grid = [int(v_x*i/10) for i in range(1, 10)]
    print(v_x_grid)
    
    # moment 버퍼 초기화
    moment = np.array([0, 0, 0])

    # "alive!!" 스레드 시작
    t_task1 = threading.Thread(target = func_thread)
    t_task1.start()

    # SDcar 모듈의 Drive 객체 생성
    car = SDcar.Drive()
    
    is_running = True # 스레드 실행 플래그
    enable_linetracing = False # 자율주행 활성화 플래그 (초기 비활성)
    
    main() # 메인 함수 실행
    
    is_running = False # 메인 함수 종료 시 스레드 종료
    car.clean_GPIO() # GPIO 정리
    print('end vis')