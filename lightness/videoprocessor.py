import numpy as np
import pprint
import time
import os
import time
import sys
import urllib
import re
from lightness.logger import Logger
from lightness.process import Process
from lightness.cmdrunner import CmdRunner
import youtube_dl
import subprocess
import math
import shlex

class VideoProcessor:

    __video_settings = None
    __logger = None
    __process = None

    # metadata about the video we are using, such as title, resolution, file extension, etc
    __video_info = None

    __DATA_DIRECTORY = 'data'

    # mp4 scales quicker than webm in ffmpeg scaling
    __YOUTUBE_DL_FORMAT = 'worst[ext=mp4]/worst'

    # a random alphanumeric string that is unlikely to be present in a video title
    __FPS_PLACEHOLDER = 'i9uoQ7dwoA9W'

    def __init__(self, video_settings, process=None):
        self.__video_settings = video_settings
        self.__process = process
        self.__logger = Logger().set_namespace(self.__class__.__name__)

    def process_and_play(self, url, video_player):
        self.__populate_video_metadata(url)

        existing_frames_file_name, video_fps = self.__get_existing_frames_file_name()
        if existing_frames_file_name:
            existing_frames_path = self.__get_data_directory() + "/" + existing_frames_file_name
            self.__logger.info("Found existing frames file: " + existing_frames_path)
            video_frames = np.load(self.__get_data_directory() + "/" + existing_frames_file_name)
            if (self.__process != None):
                self.__process.set_status(Process.STATUS_PLAYING)
            video_player.playVideo(video_frames, video_fps)
        else:
            self.__logger.info("Unable to find existing frames file. Processing video...")
            video_frames, video_fps = self.__process_and_play_video(video_player)

    # Regex match from frames save pattern to see if a file matches that with an unknown FPS.
    def __get_existing_frames_file_name(self):
        regex = self.__insert_fps_into_frames_file_name(fps = '([0-9.]+)', should_escape_save_pattern = True)
        regex = "^" + regex + "$"
        regex = re.compile(regex)

        for file in os.scandir(self.__get_data_directory()):
            if not file.is_file():
                continue
            match = regex.match(file.name)
            if match:
                fps = match.group(1)
                return [file.name, float(fps)]

        return None, None

    # we insert the video fps into the saved frames file name
    def __insert_fps_into_frames_file_name(self, fps, should_escape_save_pattern = False):
        frames_save_pattern = self.__get_frames_save_pattern(should_escape_save_pattern)
        frames_file_name = frames_save_pattern.replace(self.__FPS_PLACEHOLDER, str(fps))
        return frames_file_name

    # todo: potentially skip this step to start playback quicker by making use of '--write-info-json' option
    def __populate_video_metadata(self, url):
        ydl_opts = {
            'format': self.__YOUTUBE_DL_FORMAT,
            'logger': Logger(),
        }
        ydl = youtube_dl.YoutubeDL(ydl_opts)
        self.__video_info = ydl.extract_info(url, download = False)

        video_type = 'video_only'
        if self.__video_info['acodec'] != 'none':
            video_type = 'video+audio'
        self.__logger.info("Using: " + video_type + ":" + self.__video_info['ext'] + "@" +
            self.__get_resolution_from_video_info())

    def __get_resolution_from_video_info(self):
        return str(self.__video_info['width']) + "x" + str(self.__video_info['height'])

    def __save_frames(self, video_frames, video_fps):
        filename = self.__get_data_directory() + "/" + self.__insert_fps_into_frames_file_name(video_fps)
        self.__logger.info("Saved frames to: " + filename)
        np.save(filename,video_frames)

    # get the frames save file name with a placeholder for FPS to be inserted
    def __get_frames_save_pattern(self, should_escape_save_pattern):
        s = '%s@%s__%s__' + self.__FPS_PLACEHOLDER + 'fps.%s.npy'
        filename = s % (
            self.__video_info['title'],
            self.__get_resolution_from_video_info(),
            "color" if self.__video_settings.is_color else "bw",
            self.__video_info['ext']
        )
        return re.escape(filename)

    def __get_data_directory(self):
        save_dir = sys.path[0] + "/" + self.__DATA_DIRECTORY
        os.makedirs(save_dir, exist_ok=True)
        return save_dir

    def __process_and_play_video(self, video_player):
        ytdl_cmd = self.__get_youtube_dl_cmd()
        fps = self.__calculate_fps()

        pix_fmt = 'gray'
        bytes_per_frame = self.__video_settings.display_width * self.__video_settings.display_height
        np_array_shape = [self.__video_settings.display_height, self.__video_settings.display_width]
        if self.__video_settings.is_color:
            pix_fmt = 'rgb24'
            bytes_per_frame = bytes_per_frame * 3
            np_array_shape.append(3)

        process_and_play_vid_cmd = (
            ytdl_cmd + " | tee " +
            ">(" + self.__get_ffplay_cmd() + " > /dev/null) " + # ensure nothing is output to stdout, because we
                                                                # need to reserve stdout capture for ffmpeg's output
            ">(" + self.__get_ffmpeg_cmd(pix_fmt) + " && printf 'dunzo') " +
            "> /dev/null"
        )
        self.__logger.info('executing process and play cmd: ' + process_and_play_vid_cmd)
        process_and_play_vid_proc = subprocess.Popen(
            process_and_play_vid_cmd,
            shell = True,
            executable = '/bin/bash', # use bash so we can make use of process subsitution
            stdout = subprocess.PIPE
        )

        self.__process.set_status(Process.STATUS_PLAYING)

        start_time = None
        frame_length =  1 / fps
        last_frame = None
        has_whole_video_been_processed = False
        has_seen_any_in_bytes = False

        avg_color_frames = []
        while True:
            if not has_whole_video_been_processed:
                in_bytes = process_and_play_vid_proc.stdout.read(5)
                if in_bytes == b'dunzo':
                    has_whole_video_been_processed = True
                if not has_whole_video_been_processed:
                    # todo: ensure the num bytes we're reading is > 0
                    in_bytes += process_and_play_vid_proc.stdout.read(bytes_per_frame - 5)

            if has_whole_video_been_processed or not in_bytes:
                if not has_whole_video_been_processed:
                    self.__logger.info("no in_bytes, end of video processing.")
                    has_whole_video_been_processed = True
            else:
                has_seen_any_in_bytes = True
                if not start_time:
                    # start the video clock as soon as we see data. Ffplay probably sent its
                    # first audio data at around the same time so they stay in sync.
                    start_time = time.time() + 0.15 # Add time for better audio sync
                avg_color_frame = np.frombuffer(in_bytes, np.uint8).reshape(np_array_shape)
                avg_color_frames.append(avg_color_frame)

            if not has_seen_any_in_bytes:
                self.__logger.info("waiting for ytdl process to initialize...")
                continue

            cur_frame = max(math.floor((time.time() - start_time) / frame_length), 0)
            if cur_frame >= len(avg_color_frames):
                if has_whole_video_been_processed:
                    self.__logger.info("video done playing.")
                    break
                else:
                    self.__logger.error("video processing unable to keep up in real-time")
                    continue

            if cur_frame != last_frame:
                video_player.playFrame(avg_color_frames[cur_frame])
                last_frame = cur_frame

        process_and_play_vid_proc.wait()
        self.__save_frames(avg_color_frames, fps)
        return avg_color_frames, fps

    def __get_youtube_dl_cmd(self):
        return (
            'youtube-dl ' +
            '--output - ' + # output to stdout
            '--format ' + shlex.quote(self.__video_info['format_id']) + " " + # download the specified video quality / encoding
            shlex.quote(self.__video_info['webpage_url']) # url to download
        )

    def __get_ffmpeg_cmd(self, pix_fmt):
        return (
            'ffmpeg ' +
            '-threads 1 ' + # using one thread is plenty fast and is probably better to avoid tying up CPUs for displaying LEDs
            '-i pipe:0 ' + # read input video from stdin
            '-filter:v ' + shlex.quote( # resize video
                'scale=' + str(self.__video_settings.display_width) + 'x' + str(self.__video_settings.display_height)) + " "
            '-c:a copy ' + # don't process the audio at all
            '-f rawvideo -pix_fmt ' + shlex.quote(pix_fmt) + " " # output in numpy compatible byte format
            '-v quiet ' + # supress output of verbose ffmpeg configuration, etc
            '-stats ' + # display progress stats
            'pipe:1' # output to stdout
        )

    def __get_ffplay_cmd(self):
        return (
            "ffplay " +
            "-nodisp " + # Disable graphical display.
            "-vn " + # Disable video
            "-autoexit " + # Exit when video is done playing
            "-i pipe:0 " + # play input from stdin
            "-v quiet " + # supress verbose ffplay output
            "-infbuf" # Do not limit the input buffer size, read as much data as possible from the input as soon as possible.
                      # Without this, ffplay's stdin appears to fill up which blocks piping to ffplay. This has a side
                      # effect blocking piping to ffmpeg which causes LED video output stutter. Will this cause memory to fill up
                      # for really long videos?
        )

    def __calculate_fps(self):
        self.__logger.info("Calculating video fps...")
        fps_parts = CmdRunner(self.__logger).run(
            ('ffprobe', '-v', '0', '-of', 'csv=p=0', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate', self.__video_info['url'])
        )
        fps_parts = fps_parts.split('/')
        fps = float(fps_parts[0]) / float(fps_parts[1])
        self.__logger.info('Calculated video fps: ' + str(fps))
        return fps
