#my code!
import time
import cv2
import lgpio
import numpy as np
from PIL import Image
from escpos.printer import Usb

#config
BUTTON_PIN = 7
USB_VID = 0x28e9  #vendor id
USB_PID = 0x0289  #product id

h = lgpio.gpiochip_open(0)
lgpio.gpio_claim_input(h, BUTTON_PIN, lgpio.SET_PULL_UP)


def init_camera():
  #force V4L2 backend
  cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
  cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
  cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
  return cap


cap = init_camera()

#fullscreen prev
cv2.namedWindow("Photo Booth", cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty("Photo Booth", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)


def get_printer():
  try:
    return Usb(
        idVendor=USB_VID,
        idProduct=USB_PID,
        in_ep=0x81,
        out_ep=0x03,
        timeout=0,
    )
  except Exception as e:
    print(f"printer not found or error: {e}")
    return None


def print_image(image_path):
  printer = get_printer()
  if not printer:
    print("skipping print: printer not connected.")
    return

  try:
    im = Image.open(image_path)
    width, height = im.size
    new_width = 384
    new_height = int((new_width / width) * height)
    im = im.resize((new_width, new_height)).convert("1")

    printer.image(im)
    printer.ln(2)
    printer.cut()
    printer.close()
    print("Printed successfully!")
  except Exception as e:
    print(f"printing failed: {e}")


print("photobooth started. press the button on GPIO 7")

try:
  while True:
    ret, frame = cap.read()
    if not ret:
      print("cam frame lost. reconnecting now...")
      cap.release()
      time.sleep(2.0)
      cap = init_camera()
      continue

    #flip
    frame = cv2.flip(frame, 1)

    #prev
    display_frame = frame.copy()
    cv2.putText(
        display_frame,
        "PRESS BUTTON TO START",
        (50, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.2,
        (0, 255, 0),
        3,
        cv2.LINE_AA,
    )

    cv2.imshow("Photo Booth", display_frame)

    # Check if button is pressed (GPIO 7 goes LOW with pull-up)
    if lgpio.gpio_read(h, BUTTON_PIN) == 0:
      print("Button pressed! Starting countdown...")

      # 3, 2, 1 Countdown overlay
      for i in [3, 2, 1]:
        start_time = time.time()
        while time.time() - start_time < 1.0:
          ret, count_frame = cap.read()
          if not ret:
            break
          count_frame = cv2.flip(count_frame, 1)

          cv2.putText(
              count_frame,
              str(i),
              (int(count_frame.shape[1] / 2) - 50, int(count_frame.shape[0] / 2)),
              cv2.FONT_HERSHEY_SIMPLEX,
              5.0,
              (0, 0, 255),
              8,
              cv2.LINE_AA,
          )
          cv2.imshow("Photo Booth", count_frame)
          cv2.waitKey(1)

      #capture
      ret, final_frame = cap.read()
      if ret:
        final_frame = cv2.flip(final_frame, 1)

        #flash effect
        white_frame = np.ones_like(final_frame) * 255
        cv2.imshow("Photo Booth", white_frame)
        cv2.waitKey(200)

        #store image locally but always be writing over
        photo_path = "/home/hannahlevine117/booth_capture.jpg"
        cv2.imwrite(photo_path, final_frame)
        print(f"Photo saved to {photo_path}")

        #printing screen
        cv2.putText(
            final_frame,
            "PRINTING...",
            (int(final_frame.shape[1] / 2) - 150, int(final_frame.shape[0] / 2)),
            cv2.FONT_HERSHEY_SCRIPT_COMPLEX,
            1.5,
            (255, 0, 0),
            4,
            cv2.LINE_AA,
        )
        cv2.imshow("Photo Booth", final_frame)
        cv2.waitKey(1)

        #send to printer
        print_image(photo_path)
        time.sleep(2)  #cool down

    if cv2.waitKey(1) & 0xFF == ord("q"):
      break

finally:
  cap.release()
  cv2.destroyAllWindows()
  lgpio.gpiochip_close(h)
