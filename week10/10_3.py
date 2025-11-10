import cv2
import numpy as np

img = cv2.imread("1.jpg", cv2.IMREAD_COLOR)

if img is not None:
    img = cv2.resize(img, (400, 300))
    print('img shape : ', img.shape)

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    yellow_lower = np.array([20, 100, 100])
    yellow_upper = np.array([30, 255, 255])

    yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)

    result = cv2.bitwise_and(img, img, mask=yellow_mask)

    img_1ch = img.copy()
    img_1ch[:, :, 0] = 0
    img_1ch[:, :, 2] = 0

    cv2.imshow("img", img)
    cv2.imshow("yellow detected", result)

    cv2.waitKey(0)
    cv2.destroyAllWindows()

else:
    print("Img file not found")