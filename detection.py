import cv2
import numpy as np
import imutils
from PIL import Image
from keras.models import load_model
import random

class RoadSigns:
    def __init__(self):
        self.model = load_model("signsclassification.h5")  # load the model
        self.classes = {1: 'Speed limit (20km/h)',
                        2: 'Speed limit (30km/h)',
                        3: 'Speed limit (50km/h)',
                        4: 'Speed limit (60km/h)',
                        5: 'Speed limit (70km/h)',
                        6: 'Speed limit (80km/h)',
                        7: 'End of speed limit (80km/h)',
                        8: 'Speed limit (100km/h)',
                        9: 'Speed limit (120km/h)',
                        10: 'No passing',
                        11: 'No passing veh over 3.5 tons',
                        12: 'Right-of-way at intersection',
                        13: 'Priority road',
                        14: 'Yield',
                        15: 'Stop',
                        16: 'No vehicles',
                        17: 'Veh > 3.5 tons prohibited',
                        18: 'No entry',
                        19: 'General caution',
                        20: 'Dangerous curve left',
                        21: 'Dangerous curve right',
                        22: 'Double curve',
                        23: 'Bumpy road',
                        24: 'Slippery road',
                        25: 'Road narrows on the right',
                        26: 'Road work',
                        27: 'Traffic signals',
                        28: 'Pedestrians',
                        29: 'Children crossing',
                        30: 'Bicycles crossing',
                        31: 'Beware of ice/snow',
                        32: 'Wild animals crossing',
                        33: 'End speed + passing limits',
                        34: 'Turn right ahead',
                        35: 'Turn left ahead',
                        36: 'Ahead only',
                        37: 'Go straight or right',
                        38: 'Go straight or left',
                        39: 'Keep right',
                        40: 'Keep left',
                        41: 'Roundabout mandatory',
                        42: 'End of no passing',
                        43: 'End no passing veh > 3.5 tons',
                        44: 'wrong'}  # dic of all signs names and id the model can predict
        self.relevant_classes = ['Speed limit (20km/h)', 'Speed limit (30km/h)', 'Speed limit (50km/h)',
                                 'Speed limit (60km/h)', 'Speed limit (70km/h)', 'Speed limit (80km/h)',
                                 'Speed limit (100km/h)', 'Speed limit (120km/h)']  # list of the speed signs

    def identify_red(self, imag):
        """
        :param imag: the image we want to identify red signs in it
        :return: array of signs pictures found
        """
        orig = imag.copy()
        imag = imag.copy()
        mser_red = cv2.MSER_create(8, 200, 3000)
        img = imag.copy()
        img_yuv = cv2.cvtColor(img, cv2.COLOR_BGR2YUV)
        # equalize the histogram of the Y channel
        img_yuv[:, :, 0] = cv2.equalizeHist(img_yuv[:, :, 0])
        # convert the YUV image back to RGB format
        img_output = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)
        # mask to extract red
        img_hsv = cv2.cvtColor(imag, cv2.COLOR_BGR2HSV)
        lower_red_1 = np.array([0, 70, 60])
        upper_red_1 = np.array([10, 255, 255])
        mask_1 = cv2.inRange(img_hsv, lower_red_1, upper_red_1)
        lower_red_2 = np.array([170, 70, 60])
        upper_red_2 = np.array([180, 255, 255])
        mask_2 = cv2.inRange(img_hsv, lower_red_2, upper_red_2)
        mask = cv2.bitwise_or(mask_1, mask_2)
        red_mask_ = cv2.bitwise_and(img_output, img_output, mask=mask)
        red_mask = red_mask_[:500, :]
        # separating channels
        r_channel = red_mask[:, :, 2]
        g_channel = red_mask[:, :, 1]
        b_channel = red_mask[:, :, 0]
        # filtering
        filtered_r = cv2.medianBlur(r_channel, 5)
        filtered_g = cv2.medianBlur(g_channel, 5)
        filtered_b = cv2.medianBlur(b_channel, 5)
        filtered_r = 4 * filtered_r - 0.5 * filtered_b - 2 * filtered_g
        regions, _ = mser_red.detectRegions(np.uint8(filtered_r))
        hulls = [cv2.convexHull(p.reshape(-1, 1, 2)) for p in regions]
        blank = np.zeros_like(red_mask)
        cv2.fillPoly(np.uint8(blank), hulls, (0, 0, 255))  # fill a blank image with the detected hulls
        # perform some operations on the detected hulls from MSER
        kernel_1 = np.ones((3, 3), np.uint8)
        kernel_2 = np.ones((5, 5), np.uint8)
        erosion = cv2.erode(blank, kernel_1, iterations=1)
        dilation = cv2.dilate(erosion, kernel_2, iterations=1)
        opening = cv2.morphologyEx(dilation, cv2.MORPH_OPEN, kernel_2)
        _, r_thresh = cv2.threshold(opening[:, :, 2], 20, 255, cv2.THRESH_BINARY)
        cnts = cv2.findContours(r_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        max_cnts = 3  # no frame we want to detect more than 3
        if not cnts == []:
            cnts_sorted = sorted(cnts, key=cv2.contourArea, reverse=True)
            if len(cnts_sorted) > max_cnts:
                cnts_sorted = cnts_sorted[:3]
            pics = []
            for c in cnts_sorted:
                x, y, w, h = cv2.boundingRect(c)
                aspect_ratio_1 = w / h
                aspect_ratio_2 = h / w
                if aspect_ratio_1 <= 0.3 or aspect_ratio_1 > 1.2:
                    continue
                if aspect_ratio_2 <= 0.3:
                    continue
                hull = cv2.convexHull(c)
                cv2.drawContours(imag, [hull], -1, (0, 255, 0), 1)
                mask = np.zeros_like(imag)
                cv2.drawContours(mask, [c], -1, (255, 255, 255), -1)  # Draw filled contour in mask
                cv2.rectangle(mask, (x, y), (int(x + w), int(y + h)), (255, 255, 255), -1)
                out = np.zeros_like(imag)  # Extract out the object and place into output image
                out[mask == 255] = imag[mask == 255]
                x_pixel, y_pixel, _ = np.where(mask == 255)
                (topx, topy) = (np.min(x_pixel), np.min(y_pixel))
                (botx, boty) = (np.max(x_pixel), np.max(y_pixel))
                if np.abs(topx - botx) <= 15 or np.abs(topy - boty) <= 15:
                    continue
                out = orig[topx - 5:botx + 5, topy - 5:boty + 5]
                if out.any():
                    out_resize = cv2.resize(out, (64, 64), interpolation=cv2.INTER_CUBIC)
                    pics.append(out_resize)
            return pics

    def classify(self, image):
        """
        :param image: photo of sign
        :return: The name of the sign that has been detected for the photo
        """
        image = image.resize((32, 32))
        image = np.expand_dims(image, axis=0)
        image = np.array(image)
        prob = self.model.predict(image)
        pred = np.argmax(prob)
        if prob[0][pred] > 0.9:
            sign = self.classes[pred + 1]
            if sign in self.relevant_classes:
                return sign
            else:
                return None
        else:
            return None

    def single_image(self, imag):
        """
        :param imag: image to detect and classify signs
        :return: name of a sign that found / None if not found
        """
        signs = self.identify_red(imag)
        for s in signs:
            color_coverted = cv2.cvtColor(s, cv2.COLOR_BGR2RGB)
            PIL_image = Image.fromarray(color_coverted)
            sign = self.classify(PIL_image)
            # rnd = random.randint(1, 1000)
            # PIL_image.save('D://Documents//Linoy//project//imgs//' + str(rnd) + '.jpg')
            if sign is not None:
                return sign
            else:
                return None
        return None


