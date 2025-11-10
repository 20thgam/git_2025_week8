import numpy as np
import cv2
import os

haar_path = cv2.data.haarcascades
face_xml_path = os.path.join(haar_path, 'haarcascade_frontalface_default.xml')
eye_xml_path = os.path.join(haar_path, 'haarcascade_eye.xml')

face_cascade = cv2.CascadeClassifier(face_xml_path)
eye_cascade = cv2.CascadeClassifier(eye_xml_path)

if face_cascade.empty():
    print(f"오류: 얼굴 XML 파일 로드 실패. 경로: {face_xml_path}")
    exit()
if eye_cascade.empty():
    print(f"오류: 눈 XML 파일 로드 실패. 경로: {eye_xml_path}")
    exit()

cap = cv2.VideoCapture(0, cv2.CAP_V4L)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

while (True):
    ret, img = cap.read()
    img = cv2.flip(img, -1)
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.2, 5)
    print("Number of faces detected: " + str(len(faces)))
    
    for (x, y, w, h) in faces:
        img = cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 1)
        roi_gray = gray[y:y + h, x:x + w]
        roi_color = img[y:y + h, x:x + w]
        eyes = eye_cascade.detectMultiScale(roi_gray)
        for (ex, ey, ew, eh) in eyes:
            cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 1)
            
    cv2.imshow('img', img)
    k = cv2.waitKey(30) & 0xff
    if k == 27:
        break

cap.release()
cv2.destroyAllWindows()