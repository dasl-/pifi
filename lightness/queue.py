import os
import sys
import ast
import signal
import subprocess
import time
from process import Process
from db import DB

class Queue:

    __db = None
    __video_proc = None
    __current_video = None

    def __init__(self):
        self.__db = DB()

    def playVideo(self, video):
        command = ["python3", "/home/pi/lightness/video", "--url", video["url"]]

        if video["is_color"]:
            command.append("--color")

        command.append("--flip-x")
        self.__video_proc = subprocess.Popen(command, stdout=subprocess.PIPE)
        self.__db.setCurrentVideo(video["id"], self.__video_proc.pid)

    def fetchCurrentVideo(self):
        self.__current_video = self.__db.getCurrentVideo()
        return self.__current_video

    def checkCurrentSignal(self):
        if self.__current_video is not None and self.__current_video["signal"] == Process.SIGNAL_KILL:
            if self.__video_proc is not None and self.__video_proc.pid == self.__current_video["pid"]:
                # kill the process
                try:
                    print("KILL PID " + str(self.__video_proc.pid))
                    os.kill(self.__video_proc.pid, signal.SIGTERM)
                except OSError:
                    print("invalid process")

                # Update the db status
                self.__db.endVideo(self.__current_video["id"])

    def checkVideoStatus(self):
        if self.__current_video is not None:
            if self.__video_proc is not None and self.__video_proc.poll() is not None:
                # the process has ended
                self.__db.endVideo(self.__current_video["id"])
            elif self.__video_proc is None:
                # the queue has no reference to a process, so it never ran it, mark the video as dead so we can proceed
                self.__db.endVideo(self.__current_video["id"])

    def checkForNextVideo(self):
        if self.__current_video is None:
            # pick up the next video
            next_video = self.__db.getNextVideo()
            if next_video is not None:
                if next_video["status"] != Process.STATUS_LOADING:
                  self.playVideo(next_video)

queue = Queue()

while(True):
    if queue.fetchCurrentVideo() is not None:
        # check for control signals on the current video
        queue.checkCurrentSignal()

        # check the video process to see if it died
        queue.checkVideoStatus()
    else:
        # get the next video if there isnt a current one
        queue.checkForNextVideo()

    time.sleep(.1)
