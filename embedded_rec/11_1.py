import cv2 as cv
import numpy as np
import threading, time
import SDcar

def func_thread():
    i = 0
    while True:
        print("alive!!")
        time.sleep(1)
        i = i+1
        if is_running is False:
            break

def key_cmd(which_key):
    print(which_key, which_key)
    is_exit = False
    if which_key & 0xFF == 184:
        print('up')
        car.motor_go(25)
    elif which_key & 0xFF == 178:
        print('down')
        car.motor_back(25)
    elif which_key & 0xFF == 180:
        print('left')
        car.motor_left(25)
    elif which_key & 0xFF == 182:
        print('right')
        car.motor_right(25)
    elif which_key & 0xFF == 181:
        print('stop')
        car.motor_stop()
    elif which_key & 0xFF == ord('q'):
        car.motor_stop()
        print('exit')
        is_exit = True
    return is_exit

def detect_line_mask(frame):
    """
    Detect only yellow lines in the frame and return the mask.
    """
    hsv = cv.cvtColor(frame, cv.COLOR_BGR2HSV)

    # 노란색 범위 조정 (더 넓은 범위로 변경)
    yellow_lower = np.array([15, 70, 70]) # Hue, Saturation, Value
    yellow_upper = np.array([35, 255, 255])

    # 노란색 마스크 생성
    yellow_mask = cv.inRange(hsv, yellow_lower, yellow_upper)

    return yellow_mask

def line_tracing(cx, width, car, tolerance=30, speed=40):
    """
    Perform line tracing based on the detected center of the contour.
    """
    center_x = width // 2
    diff = cx - center_x

    if abs(diff) <= tolerance: # 중심 차이가 허용 범위 내
        car.motor_go(speed)
        print("go")
    elif diff > 0: # 중심이 오른쪽
        car.motor_right(speed)
        print("right")
    else: # 중심이 왼쪽
        car.motor_left(speed)
        print("left")

def main():
    camera = cv.VideoCapture(0)
    camera.set(cv.CAP_PROP_FRAME_WIDTH, v_x)
    camera.set(cv.CAP_PROP_FRAME_HEIGHT, v_y)

    try:
        while camera.isOpened():
            ret, frame = camera.read()
            if not ret:
                print("can't read frame.")
                break

            frame = cv.flip(frame, -1)
            crop_img = frame[120:, :] # 아래쪽 120 픽셀을 자름 (도로 영역 가정)

            # 노란색 라인 탐지
            mask = detect_line_mask(crop_img)
            contours, _ = cv.findContours(mask, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)

            if len(contours) > 0:
                # 가장 큰 윤곽을 기준으로 중심 좌표 계산
                largest_contour = max(contours, key=cv.contourArea)
                moments = cv.moments(largest_contour)

                # 중심 좌표 계산 (분모가 0이 되는 것을 방지하기 위해 입실론 추가)
                if moments['m00'] != 0:
                    cx = int(moments['m10'] / moments['m00'])
                    cy = int(moments['m01'] / moments['m00'])

                    # 중심 표시
                    cv.circle(crop_img, (cx, cy), 5, (0, 0, 255), -1)
                    cv.drawContours(crop_img, [largest_contour], -1, (255, 0, 0), 2)

                    # 라인트레이싱 실행
                    line_tracing(cx, crop_img.shape[1], car)

            # 그리드 추가
            show_grid(crop_img)

            # 결과 출력
            cv.imshow("crop_img", crop_img)

            # 키 입력 처리
            is_exit = False
            which_key = cv.waitKey(20)
            if which_key > 0:
                is_exit = key_cmd(which_key)
            
            if is_exit is True:
                cv.destroyAllWindows()
                break

    except Exception as e:
        print(e)
        global is_running
        is_running = False
    finally:
        camera.release()

def show_grid(img):
    h, _, _ = img.shape
    for x in v_x_grid:
        cv.line(img, (x,0), (x,h), (0,255,0), 1, cv.LINE_4)

if __name__ == '__main__':
    v_x = 320
    v_y = 240
    v_x_grid = [int(v_x*i/10) for i in range(1, 10)]

    moment = np.array([0, 0, 0])

    print(v_x_grid)

    t_task1 = threading.Thread(target=func_thread)
    t_task1.start()

    car = SDcar.Drive()

    is_running = True
    main()

    is_running = False
    car.clean_GPIO()