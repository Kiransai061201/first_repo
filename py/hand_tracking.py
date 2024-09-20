import cv2
import mediapipe as mp
import pyautogui

cam = cv2.VideoCapture(0)

mpHands = mp.solutions.hands
hands = mpHands.Hands()
mpDraw = mp.solutions.drawing_utils
screen_w, screen_h = pyautogui.size()
index_y = 0
while True:
    success, img = cam.read()
    img = cv2.flip(img,1)
    frame_h, frame_w, _ = img.shape
    imgRGB = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
    results = hands.process(imgRGB)

    # print(results.multi_hand_landmarks)

    if results.multi_hand_landmarks:
        for handLMs in results.multi_hand_landmarks:
            mpDraw.draw_landmarks(img, handLMs,mpHands.HAND_CONNECTIONS)
            landmarks = handLMs.landmark
            for id,landmark in enumerate(landmarks):
                x = int(landmark.x * frame_w)
                y = int(landmark.y * frame_h)
                # print(x,y)
                if id == 8:
                    cv2.circle(img = img, center = (x,y), radius=20, color=(0,255,255),thickness= 3)
                    index_x  = screen_w/frame_w * x
                    index_y = screen_h/frame_h * y
                    pyautogui.moveTo(index_x,index_y)

                if id == 4:
                    cv2.circle(img = img, center = (x,y), radius=20, color=(0,255,255),thickness= 3)
                    thumb_x  = screen_w/frame_w * x
                    thumb_y = screen_h/frame_h * y
                    print(abs(index_y - thumb_y))
                    if abs(index_y - thumb_y) < 20:
                        pyautogui.click()
                        pyautogui.sleep(1)

    cv2.imshow("Image",img)
    cv2.waitKey(1)