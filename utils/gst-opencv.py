# vimcmd: python3 %
import time

import cv2
import v4l2ctl


def find_v4l2loopback():
    DEV_RANGE = 6

    # Scan for possible loopback devices
    for ii in range(DEV_RANGE):
        device = v4l2ctl.V4l2Device(ii)
        if "v4l2loopback" in device.bus:
            dev_fd = "/dev/video%s" % ii
            print("Found loopback device at %s" % dev_fd)
            return dev_fd

    # If not found
    raise Exception("No loopback device found in range %d" % DEV_RANGE)


# Cam properties
fps = 30.0
frame_width = 640
frame_height = 480

# Create capture
cap = cv2.VideoCapture(0)

# Set camera properties
cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)
cap.set(cv2.CAP_PROP_FPS, fps)


# Check if cap is open
if cap.isOpened() is not True:
    print("Cannot open camera. Exiting.")
    quit()

out = cv2.VideoWriter(
    "appsrc ! videoconvert ! v4l2sink device=%s" % (
            find_v4l2loopback(),
        ),
    0,
    fps,
    (frame_width, frame_height),
    True
)

while True:
    ret, frame = cap.read()
    if ret is True:
        frame = cv2.flip(frame, 1)
        out.write(frame)
    else:
        print("Camera error.")
        time.sleep(1)

cap.release()
