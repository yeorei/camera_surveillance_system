import cv2, threading, datetime
import os, ssl, smtplib, math
from email.message import EmailMessage
from .models import *

class VideoCamera(object):
    def __init__(self):
        # capture camera feed
        self.video = cv2.VideoCapture(0)

        # get frame rate
        self.fps = int(self.video.get(cv2.CAP_PROP_FPS))

        # opencv background subtractor
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=50, varThreshold=40)

        # object tracking variables
        self.obj_id = 0
        self.direction = None
        self.centre_pt_curr = []
        self.centre_pt_prev = []
        self.objs = {}

        # opencv video codec (mp4 format)
        self.fourcc = cv2.VideoWriter_fourcc('M','J', 'P', 'G')

        # obtain user profile model
        user_info = UserProfile.objects.latest('id')
        
        # recording variables
        self.path = user_info.path
        self.max_len = 20 * self.fps
        self.frame_count = 0
        self.writer = None
        
        # alert variables
        self.alert_on = user_info.alert_on
        self.alert_sent = False
        self.alert_counter = 0

        # email accounts
        self.email_recipient = user_info.email
        self.email_sender = 'camerasurveillanceapp@gmail.com'
        self.email_password = os.environ.get('CS_EMAIL_PASSWORD')

    def __del__(self):
        self.video.release()

    def send_email(self, direction):
        # specify email content
        em = EmailMessage()
        em['From'] = self.email_sender
        em['To'] = self.email_recipient
        em['Subject'] = 'Camera Surveillance Alert'
        em.set_content('Motion has been detected in the room. Object is moving ' + direction + '.')

        # login and send email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=ssl.create_default_context()) as smtp:
            smtp.login(self.email_sender, self.email_password)
            smtp.sendmail(self.email_sender, self.email_recipient, em.as_string())

    def new_video(self, direction):
        # get datetime info
        curr_datetime = datetime.datetime.now()
        name = curr_datetime.strftime('%Y-%m-%d-%H-%M-%S')
        date = curr_datetime.strftime('%d %b %Y')
        time = curr_datetime.strftime('%I:%M %p')

        if time[0] == '0':
            time = time.replace(time[0], '')

        # create new video
        file = os.path.join(self.path, name)
        writer = cv2.VideoWriter(file+'.avi', self.fourcc, self.fps, (640, 360))

        description = 'Object detected moving ' + direction + '.'

        # save video and datetime info to database
        recording = Recording(name = name, date = date, time = time, description = description, file = file+'.avi')
        recording.save()

        return writer

    def get_frame(self):
        check, frame = self.video.read()
        frame = cv2.resize(frame, (640, 360))

        if self.alert_on:
            # OBJECT DETECTION
            # noise reduction (smoothening)
            blur_frame = cv2.GaussianBlur(frame, (25, 25), 0)
            
            # create mask
            mask = self.bg_subtractor.apply(blur_frame)
            
            # convert to b&w
            threshold_mask = cv2.threshold(mask, 5, 255, cv2.THRESH_BINARY)[1]
            
            # extract contours
            contours, _ = cv2.findContours(threshold_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # OBJECT TRACKING
            # draw green bounding rectangles around each detected object
            for c in contours:
                if cv2.contourArea(c) > 1000:
                    (x, y, w, h) = cv2.boundingRect(c)
                    
                    # get centre of bounding rectangles
                    cx = int((2*x + w) / 2)
                    cy = int((2*y + h) / 2)
                    self.centre_pt_curr.append((cx, cy))
            
            # copy arrays to allow looping and deletion
            objs_copy = self.objs.copy()
            centre_pt_curr_copy = self.centre_pt_curr.copy()

            # identify objects and determine direction of travel 
            for id, pt2 in objs_copy.items():
                object_exists = False
                for pt in centre_pt_curr_copy:
                    # calculate the distance between the centre points in the previous and current frame
                    distance = math.hypot(pt2[0] - pt[0], pt2[1] - pt[1])

                    # if the centre points are close enough, they belong to an existing object
                    if distance < 40:
                        object_exists = True

                        # calculate x-value difference to determine the direction of travel (left or right)
                        if (pt2[0] - pt[0]) > 5:
                            self.direction = 'left'
                        elif (pt2[0] - pt[0]) < 5:
                            self.direction = 'right'
                        else:
                            self.direction = pt2[2]

                        # update with new position and direction
                        self.objs[id] = (pt[0], pt[1], self.direction)

                        # remove the centre point as it has been evaluated
                        if pt in self.centre_pt_curr:
                            self.centre_pt_curr.remove(pt)
                        continue

                # remove lost ids for objects out of view
                if not object_exists:            
                    self.objs.pop(id)

            # add new ids for new objects that enter the frame
            for pt in self.centre_pt_curr:
                self.objs[self.obj_id] = (pt[0], pt[1], self.direction)
                self.obj_id += 1
            
            # make a copy of the centre points for comparison
            self.centre_pt_prev = self.centre_pt_curr.copy()

            # EMAIL ALERT
            # increase alert_counter if there is significant movement
            if threshold_mask.sum() > 10000 and self.alert_counter < 20:
                self.alert_counter += 1
            else:
                if self.alert_counter > 0:
                    self.alert_counter -= 1
            
            # consider potential threat if there is significant movement for at least 20 frames
            if self.alert_counter > 10:

                # create video writer if it does not exist
                if not self.writer:
                    self.writer = self.new_video(self.direction,)

                # capture frames until a maximum of 20 seconds
                if self.frame_count <= self.max_len:
                    self.writer.write(frame)
                    self.frame_count += 1
                   
                else:
                    self.writer.release()                                                        
                    self.frame_count = 0
                    self.writer = self.new_video(self.direction,)

                # send email alert
                if not self.alert_sent:
                    alert = threading.Thread(target=self.send_email, args=(self.direction,))
                    alert.start()
                    self.alert_sent = True

            # reset if there is no movement for over 20 frames
            if self.alert_counter == 0:
                self.alert_sent = False                
                self.frame_count = 0              
                if self.writer:
                    self.writer.release()
                                
        # (for demonstration purposes) show variables on screen
        cv2.putText(frame, 'alert mode: ' + str(self.alert_on), (10, 25), 0, 0.5, 0, 1)
        cv2.putText(frame, 'alert counter: ' + str(self.alert_counter), (10, 50), 0, 0.5, 0, 1)
        cv2.putText(frame, 'alert sent: ' + str(self.alert_sent), (10, 75), 0, 0.5, 0, 1)

        ret, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes()