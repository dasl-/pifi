import os
import sys
import ast
import signal
import subprocess
import time
import threading
from lightness.process import Process
from lightness.db import DB

class Queue(threading.Thread):

    __db = None
    __video_proc = None
    __current_video = None
    __additional_video_args = []

    def __init__(self, additional_video_args=[]):
        threading.Thread.__init__(self)
        self.__db = DB()
        self.__additional_video_args = additional_video_args
        self._stop_event = threading.Event()

    def run(self):
        while(not self.stopped()):
            self.__check_cycle()
            time.sleep(.1)

    def stop(self):
        self._stop_event.set()
        self.__kill_current_video()

    def stopped(self):
        return self._stop_event.is_set()

    def __check_cycle(self):
        if self.__fetch_current_video() is not None:
            # check for control signals on the current video
            self.__check_current_signal()

            # check the video process to see if it died
            self.__check_video_status()
        else:
            # get the next video if there isnt a current one
            self.__check_for_next_video()

    def __play_video(self, video):
        command = ["python3", "/home/pi/lightness/video", "--url", video["url"]]

        if video["is_color"]:
            command.append("--color")

        # add global arguments to the video player
        command = command + self.__additional_video_args

        self.__video_proc = subprocess.Popen(command, stdout=subprocess.PIPE)
        self.__db.setCurrentVideo(video["id"], self.__video_proc.pid)

    def __fetch_current_video(self):
        self.__current_video = self.__db.getCurrentVideo()
        return self.__current_video

    def __check_current_signal(self):
        if self.__current_video is not None and self.__current_video["signal"] == Process.SIGNAL_KILL:
            self.__kill_current_video()

    def __kill_current_video(self):
        if self.__video_proc is not None and self.__video_proc.pid == self.__current_video["pid"]:
            # kill the process
            try:
                print("KILL PID " + str(self.__video_proc.pid))
                os.kill(self.__video_proc.pid, signal.SIGTERM)
            except OSError:
                print("invalid process")

            # Update the db status
            self.__db.endVideo(self.__current_video["id"])

            # todo: clear the screen

    def __check_video_status(self):
        if self.__current_video is not None:
            if self.__video_proc is not None and self.__video_proc.poll() is not None:
                # the process has ended
                self.__db.endVideo(self.__current_video["id"])
            elif self.__video_proc is None:
                # the queue has no reference to a process, so it never ran it, mark the video as dead so we can proceed
                self.__db.endVideo(self.__current_video["id"])

    def __check_for_next_video(self):
        if self.__current_video is None:
            # pick up the next video
            next_video = self.__db.getNextVideo()
            if next_video is not None:
                if next_video["status"] != Process.STATUS_LOADING:
                  self.__play_video(next_video)
