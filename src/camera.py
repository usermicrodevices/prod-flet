import base64, io, logging, threading

import flet as ft
import cv2#pip install opencv-python
#from PIL import Image#pip install pillow
#from pyzbar import pyzbar#pip install pyzbar # but it required C-extension libzbar and not build with mobile platforms
#from third_party.pyzbar import pyzbar#fixed version with C-extensions included
#import zxingcpp
from third_party.EAN13_Reader import decode_simple


DEFAULT_BASE64 = 'R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=='


class CryptoHandlerMaster():
    def validate_data(self, value):
        return True, value.data.decode('utf-8')


class CameraMaster(ft.Image):

    def __init__(self, *args, **kwargs):
        page = kwargs.pop('page')
        logging.debug(['‼⚠ PAGE ⚠‼', page])
        self.qr_reader_callback = kwargs.pop('reader_callback')
        self.is_a_qr_reader = kwargs.pop('is_qr_reader', True)

        kwargs['fit'] = ft.ImageFit.FILL
        kwargs['src_base64'] = DEFAULT_BASE64

        super().__init__(*args, **kwargs)

        self.crypto_handler = CryptoHandlerMaster()

        self.cap = None
        # Find the available camera
        camera_index = self.find_available_camera()
        if camera_index is None:
            logging.debug('‼⚠ No available camera found. ⚠‼')
        else:# Initialize the camera
            self.cap = cv2.VideoCapture(camera_index)

        # Event to control the update loop
        self.stop_event = threading.Event()
        # Start the periodic image update in a separate thread
        self.update_thread = threading.Thread(target=self.update_image)
        self.update_thread.start()

        self.page = page

    def __del__(self):
        self.close()

    def __str__(self) -> str:
        return 'CameraMaster'

    def __repr__(self) -> str:
        return 'CameraMaster'

    def is_mounted(self) -> bool:
        if self.page is None:
            return False
        for view in self.page.views:
            for control in view.controls:
                if self == control.content:
                    return True
        return False

    def find_available_camera(self, max_index=10):
        for index in range(max_index):
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                cap.release()
                return index
        return None

    def update_image(self):
        while not self.stop_event.is_set():
            if not self.cap:
                camera_index = self.find_available_camera()
                if camera_index is None:
                    logging.debug('‼⚠ No available camera found. ⚠‼')
                    self.stop_event.wait(5)
                    continue
                else:
                    self.cap = cv2.VideoCapture(camera_index)

            #logging.basicConfig(level=logging.INFO)
            ret, frame = self.cap.read()
            if ret:
                if self.is_a_qr_reader == True:
                    # Get frame dimensions
                    height, width, _ = frame.shape

                    # Define the rectangle dimensions (centered)
                    rect_width, rect_height = 400, 350
                    top_left = (width // 2 - rect_width // 2, height // 2 - rect_height // 2)
                    bottom_right = (width // 2 + rect_width // 2, height // 2 + rect_height // 2)
                    color = (255, 255, 255)  # White color in BGR
                    thickness = 2
                    style = 'dashed'

                    # Apply dark overlay outside the rectangle
                    frame = self.apply_overlay(frame, top_left, bottom_right)

                    # Draw the dashed rectangle on top of the frame
                    self.drawrect(frame, top_left, bottom_right, color, thickness, style)

                    # Scan QR codes within the rectangle
                    frame, valid_objects = self.scan_qr_codes_within_rect(frame, top_left, bottom_right)
                    if valid_objects and self.qr_reader_callback:
                        #valid_objects = zxingcpp.read_barcodes(frame)
                        # for obj in valid_objects:
                        #     if self.qr_reader_callback != None and obj['is_valid'] == True:
                        #         self.qr_reader_callback(obj['data'])
                        ean13, is_valid, thresh = decode_simple.decode(frame)
                        if self.qr_reader_callback != None and is_valid:
                            self.qr_reader_callback(ean13)

                #pil_im = Image.fromarray(cv2.threshold(frame, 127, 255, cv2.THRESH_BINARY)[1])
                #pil_im = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                #buf = io.BytesIO()
                #pil_im.save(buf, format='PNG')
                #self.src_base64 = base64.b64encode(buf.getvalue()).decode()
                #self._set_attr_internal('srcBase64', base64.b64encode(buf.getvalue()).decode())

                _, buf = cv2.imencode('.png', frame)
                self.src_base64 = base64.b64encode(buf).decode('utf-8')

                try:
                    self.update()
                except Exception:
                    break

            # Sleep for XXX ms
            self.stop_event.wait(0.01)
            #logging.basicConfig(level=logging.DEBUG)

    def close(self):
        self.stop_event.set()
        if self.cap:
            self.cap.release()
        self.update_thread.join()

    def on_close(self, e):
        self.close()

    def drawline(self, img, pt1, pt2, color, thickness=1, style='dashed', dash_length=10, gap_length=10):
        dist = ((pt1[0] - pt2[0]) ** 2 + (pt1[1] - pt2[1]) ** 2) ** 0.5
        num_dashes = int(dist / (dash_length + gap_length))

        for i in range(num_dashes):
            start = (
                int(pt1[0] + (pt2[0] - pt1[0]) * (i * (dash_length + gap_length)) / dist),
                int(pt1[1] + (pt2[1] - pt1[1]) * (i * (dash_length + gap_length)) / dist)
            )
            end = (
                int(pt1[0] + (pt2[0] - pt1[0]) * ((i * (dash_length + gap_length)) + dash_length) / dist),
                int(pt1[1] + (pt2[1] - pt1[1]) * ((i * (dash_length + gap_length)) + dash_length) / dist)
            )

            cv2.line(img, start, end, color, thickness)

    def drawpoly(self, img, pts, color, thickness=1, style='dashed'):
        s = pts[0]
        e = pts[0]
        pts.append(pts.pop(0))
        for p in pts:
            s = e
            e = p
            self.drawline(img, s, e, color, thickness, style)

    def drawrect(self, img, pt1, pt2, color, thickness=1, style='dashed'):
        # Draw the dashed rectangle on the frame
        pts = [pt1, (pt2[0], pt1[1]), pt2, (pt1[0], pt2[1])]
        self.drawpoly(img, pts, color, thickness, style)

    def apply_overlay(self, img, rect_pt1, rect_pt2):
        # Create a dark overlay
        overlay = img.copy()
        overlay[:] = (0, 0, 0)  # Dark color
        alpha = 0.4  # Overlay transparency

        # Draw a white rectangle to cover the area inside the dashed rectangle
        cv2.rectangle(overlay, rect_pt1, rect_pt2, (255, 255, 255), cv2.FILLED)

        # Blend the overlay with the original image
        img = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0)
        return img

    def scan_qr_codes_within_rect(self, frame, rect_pt1, rect_pt2):
        #decoded_objects = pyzbar.decode(frame)
        decoded_objects = []
        valid_objects = []
        list_of_valid_objects_to_return = []
        for obj in decoded_objects:

            # qr_data = obj.data.decode("utf-8")
            # qr_type = obj.type
            # text = f'{qr_data} ({qr_type})'
            is_valid, qr_data = self.crypto_handler.validate_data(obj.data.decode("utf-8"))
            color = (0, 255, 0) if is_valid else (0, 0, 255)
            text = f'({qr_data['name']})' if is_valid else f'(Invalid)'

            object_to_return = {
                'data': qr_data,
                'is_valid': is_valid,
            }
            list_of_valid_objects_to_return.append(object_to_return)

            # Draw the bounding box and text on the frame
            points = obj.polygon
            if len(points) > 4:
                hull = cv2.convexHull(points)
                points = hull
            points = list(points)
            for j in range(len(points)):
                cv2.line(frame, tuple(points[j]), tuple(points[(j + 1) % len(points)]), color, 3)

            # Draw the text on the frame
            cv2.putText(frame, text, (points[0].x, points[0].y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            center_x = (obj.rect.left + obj.rect.left + obj.rect.width) // 2
            center_y = (obj.rect.top + obj.rect.top + obj.rect.height) // 2
            if rect_pt1[0] <= center_x <= rect_pt2[0] and rect_pt1[1] <= center_y <= rect_pt2[1]:
                valid_objects.append(obj)

        #return frame, valid_objects
        return frame, list_of_valid_objects_to_return
