#! /usr/bin/env python3

from imutils.video import VideoStream
import imutils
import time
import cv2
import re
import v4l2ctl

OPENCV_OBJECT_TRACKERS = {
    "c": {"name": "Csrt", "method": cv2.legacy.TrackerCSRT_create},
    "k": {"name": "Kcf", "method": cv2.legacy.TrackerKCF_create},
    "b": {"name": "Boosting", "method": cv2.legacy.TrackerBoosting_create},
    "m": {"name": "Mil", "method": cv2.legacy.TrackerMIL_create},
    "t": {"name": "Tld", "method": cv2.legacy.TrackerTLD_create},
    "f": {"name": "medianFlow", "method": cv2.legacy.TrackerMedianFlow_create},
    "o": {"name": "mOsse", "method": cv2.legacy.TrackerMOSSE_create},
}
tracker_display_names = [ii["name"] for ii in OPENCV_OBJECT_TRACKERS.values()]


def has_gstreamer():
    match = re.findall("GStreamer:\s+YES", cv2.getBuildInformation())
    return bool(match)


def find_v4l2loopback():
    DEV_RANGE = 6

    # Scan for possible loopback devices
    for ii in range(DEV_RANGE):
        device = v4l2ctl.V4l2Device(ii)
        if "v4l2loopback" in device.bus:
            dev_fd = "/dev/video%s" % ii
            # print("Found loopback device at %s" % dev_fd)
            return dev_fd

    # If not found
    return None


class Timer:
    def __init__(self, avg=1):
        self.__tic = None
        self.__tac = None
        self.buffer = [None] * avg

    def tic(self):
        self.__tic = time.time()

    def tac(self):
        self.__tac = time.time()
        self.buffer = self.buffer[1:] + [self.__tac - self.__tic]
        return self.time()

    def time(self):
        buf = [ii for ii in self.buffer if ii is not None]
        return sum(buf) / len(buf)


def text_embed_ip(frame, info):
    # invert list
    info = info[::-1]
    H, W = frame.shape[:2]
    for i, (k, v) in enumerate(info):
        # Black BG
        cv2.putText(
            frame, "{}: {}".format(k, v),
            (10, H - ((i * 20) + 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            4,
            cv2.LINE_AA
        )
        # White FG
        cv2.putText(
            frame, "{}: {}".format(k, v),
            (10, H - ((i * 20) + 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA
        )


# Decide on whether to stream to a v4l2loopback device
if (has_gstreamer() or print("OpenCV Gstreamer support not found.")) and \
        (find_v4l2loopback() or print("Loopback device not found.")):

    lo = find_v4l2loopback()
    print("Doing loopback to %s!" % lo)
    out = cv2.VideoWriter(
        "appsrc ! videoconvert ! v4l2sink device=%s" % lo,
        0, 30, (640, 480), True
    )
else:
    out = None


tracker = None  # will be overriden by program on keypress
bbox = None  # will be overriden by program or user

if __name__ == "__main__":
    vs = VideoStream(src=0).start()
    timer = Timer(30)

    while True:
        # Capture and resize
        frame = vs.read()
        if frame is None:
            break
        frame = imutils.resize(frame, width=500)

        # Track and report outcome
        if tracker:
            timer.tic()
            success, bbox = tracker.update(frame)
            timer.tac()
            if success:
                x, y, w, h = [int(v) for v in bbox]
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            # Update on-screen info
            text_embed_ip(frame, [
                ("Success", "Yes" if success else "No"),
                ("Tracker fps", round(1 / timer.time(), 2)),
                ("Tracker ms",  round(timer.time() * 1e3, 4)),
                ("Tracker", tracker.__class__),
                ("Choose", "/".join(tracker_display_names)),
            ])
        else:
            text_embed_ip(frame, [
                ("Mark bbox", "s"),
                ("Quit", "q"),
                ("Choose tracker", "/".join(tracker_display_names)),
            ])

        # Imshow and handle keys
        cv2.imshow("Frame", frame)
        if out:
            out.write(frame)
        key = cv2.waitKey(1) & 0xFF

        # Select a different tracker online
        if chr(key) in OPENCV_OBJECT_TRACKERS.keys():
            tracker_factory = OPENCV_OBJECT_TRACKERS[chr(key)]["method"]
            tracker = tracker_factory()

            if bbox:
                tracker.init(frame, bbox)

        # Select init bbox and start a tracker
        elif key == ord("s"):
            print("Select BBox and press Enter to continue.")
            bbox = cv2.selectROI("Frame", frame, fromCenter=False,
                                 showCrosshair=True)

            if not tracker:
                tracker_factory = OPENCV_OBJECT_TRACKERS['k']["method"]

            tracker = tracker_factory()
            tracker.init(frame, bbox)

        elif key == ord("q"):
            break

    vs.stop()
    cv2.destroyAllWindows()
