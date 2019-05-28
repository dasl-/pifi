import numpy as np
import cv2
import pafy
import pprint
import time
import os
import time
import sys
import urllib
import re
import multiprocessing
import sharedmem

class VideoProcessor:

    # Settings
    __video_settings = None

    # pafy video stream
    __video_stream = None

    __thumbnail_url = None
    __thumbnail = None

    __DATA_DIRECTORY = 'lightness_data'
    __FRAMES_FILE_FORMAT = '%s@%s__%s.%s.npy'
    __VIDEO_FILE_FORMAT = '%s@%s.%s'

    def __init__(self, url, video_settings):
        self.__video_settings = video_settings
        self.__video_stream = self.__get_video_stream(url)

    def preprocess_and_play(self, video_player):
        self.__get_and_display_thumbnail(video_player)

        existing_frames_file_name, video_fps = self.__get_existing_frames_file_name()
        if existing_frames_file_name:
            existing_frames_path = self.__get_data_directory() + "/" + existing_frames_file_name
            print("Found existing frames file: " + existing_frames_path)
            video_frames = np.load(self.__get_data_directory() + "/" + existing_frames_file_name)
        else:
            print("Unable to find existing frames file. Processing video...")
            video_frames, video_fps = self.__process_video(video_player)

        video_player.playVideo(video_frames, video_fps)

    # Regex match from frames save pattern to see if a file matches that with an unknown FPS.
    def __get_existing_frames_file_name(self):
        regex = self.__insert_fps_into_frames_file_name('([0-9.]+)', True)
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
    def __insert_fps_into_frames_file_name(self, fps, should_regex_escape):
        frames_save_pattern = self.__get_frames_save_pattern()
        dot_char = '.'
        if should_regex_escape:
            frames_save_pattern = re.escape(frames_save_pattern)
            dot_char = '\\.'

        index_of_last_dot = frames_save_pattern.rfind(dot_char)
        chopped = frames_save_pattern[:index_of_last_dot]
        index_of_penultimate_dot = chopped.rfind(dot_char)
        frames_file_name = frames_save_pattern[:index_of_penultimate_dot] + "__" + fps + "fps" + frames_save_pattern[index_of_penultimate_dot:]
        return frames_file_name

    def __get_and_display_thumbnail(self, video_player):
        try:
            req = urllib.request.urlopen(self.__thumbnail_url)
            arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
            self.__thumbnail = cv2.imdecode(arr, -1)
            self.__display_thumbnail(video_player)
        except:
            pass

    def __display_thumbnail(self, video_player):
        slice_width = (self.__thumbnail.shape[1] / self.__video_settings.display_width)
        slice_height = (self.__thumbnail.shape[0] / self.__video_settings.display_height)
        avg_color_frame = self.__get_avg_color_frame(slice_width, slice_height, self.__thumbnail)
        video_player.playFrame(avg_color_frame)

    def __get_video_stream(self, url):
        p = pafy.new(url)

        # pick lowest resolution because it will be less resource intensive to process
        best_stream = None
        lowest_x_dimension = None

        print("Options:")
        for stream in p.videostreams:
            filesize = '??'
            if (stream._info['filesize']):
                filesize = str(round(stream._info['filesize']/1024/1024, 2))

            print("    " + stream.extension + "@" + stream.resolution + " " +
                str(stream._info['fps']) + "fps " + filesize + "MB")
            if (not best_stream or
                (
                    stream.dimensions[0] <= lowest_x_dimension and
                    stream.extension == 'webm' # prefer webm because mp4s sometimes refuse to play
                )
            ):
                best_stream = stream
                lowest_x_dimension = stream.dimensions[0]
        print("Using: " + str(best_stream))
        # pprint.pprint(best_stream.__dict__)

        self.__thumbnail_url = p.thumb

        return best_stream

    def __save_frames(self, video_frames, video_fps):
        np.save(
            self.__get_data_directory() + "/" + self.__insert_fps_into_frames_file_name(str(video_fps), False),
            video_frames
        )

    # get the frames save file name without the FPS inserted into it
    def __get_frames_save_pattern(self):
        filename = self.__FRAMES_FILE_FORMAT % (
            self.__video_stream.title,
            self.__video_stream.resolution,
            "color" if self.__video_settings.is_color else "bw",
            self.__video_stream.extension
        )

        return filename

    # download video rather than streaming to avoid errors like:
    # [tls @ 0x1388940] Error in the pull function.
    # [matroska,webm @ 0x1396ff0] Read error
    # [tls @ 0x1388940] The specified session has been invalidated for some reason.
    # [tls @ 0x1388940] The specified session has been invalidated for some reason.
    def __download_video(self):
        filename = self.__VIDEO_FILE_FORMAT % (
            self.__video_stream.title,
            self.__video_stream.resolution,
            self.__video_stream.extension
        )

        save_path = (self.__get_data_directory() + "/" + filename)

        if os.path.exists(save_path):
            print("Found existing video file: " + save_path)
            return save_path
        else:
            print("Unable to find existing video file. Downloading video...")
            self.__video_stream.download(save_path)
            return save_path


    def __get_data_directory(self):
        save_dir = sys.path[0] + "/" + self.__DATA_DIRECTORY
        os.makedirs(save_dir, exist_ok=True)
        return save_dir

    def __get_next_frame(self, vid_cap, num_skip_frames):
        success = True
        # add one because we need to call .grab() once even if we're skipping no frames.
        for x in range(num_skip_frames + 1):
            success = vid_cap.grab()
            if not success:
                return False, None
        success, frame = vid_cap.retrieve()
        if not success:
            return False, None
        return success, frame

    def __process_video_subprocess(self, avg_color_frames, process_num, num_processes, video_path):
        print("[SUBPROCESS " + str(process_num) + "] Starting...")
        start_frame = process_num
        vid_cap = cv2.VideoCapture(video_path)
        success, frame = self.__get_next_frame(vid_cap, start_frame)
        if not success:
            return

        if (self.__video_settings.is_color):
            num_frames, display_width, display_height, ignore = avg_color_frames.shape
        else:
            num_frames, display_width, display_height = avg_color_frames.shape

        slice_width = vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH) / display_width
        slice_height = vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT) / display_height
        current_frame = start_frame
        loop_counter = 0
        log_freq = 1 / 200
        start = time.time()
        while (True):
            if not self.__video_settings.is_color:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

            if loop_counter != 0 and loop_counter % int(round(log_freq ** -1)) == 0:
                processing_frame_sec = str(round(vid_cap.get(cv2.CAP_PROP_POS_MSEC) / 1000, 2))
                processing_fps = str(round(loop_counter / (time.time() - start), 2))
                print("[SUBPROCESS " + str(process_num) + "] Progress: " + str(round(current_frame / num_frames * 100, 2)) + "%. " +
                    "Processing frame from " + processing_frame_sec + "s at " + processing_fps + " frames per second.")

            avg_color_frame = self.__get_avg_color_frame(slice_width, slice_height, frame)
            avg_color_frames[current_frame] = avg_color_frame
            current_frame += num_processes
            if current_frame < num_frames:
                # some videos report an incorrect frame count (less frames than it actually is).
                # Make sure we don't go over what we thought it was...
                success, frame = self.__get_next_frame(vid_cap, num_processes - 1)
                if not success:
                    print("Unable to __get_next_frame")
                    break
            else:
                break

            loop_counter += 1

        vid_cap.release()
        end = time.time()
        processing_fps = str(round(loop_counter / (end - start), 2))
        print("[SUBPROCESS " + str(process_num) + "] Processing video subprocess completed in " +
            str(round(end - start, 2)) + " seconds at " + processing_fps + " frames per second.")

    def __process_video(self, video_player):
        video_path = self.__download_video()
        vid_cap = cv2.VideoCapture(video_path)
        video_fps = vid_cap.get(cv2.CAP_PROP_FPS)
        num_frames = int(vid_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        vid_cap.release()

        avg_color_frames_shape = self.__get_avg_color_frame_shape()
        avg_color_frames_shape.insert(0, num_frames)
        avg_color_frames = sharedmem.empty(avg_color_frames_shape, dtype=np.uint8)
        num_processes = multiprocessing.cpu_count()
        processes = []
        start = time.time()
        for process_num in range(num_processes):
            processes.append(sharedmem.background(
                function = self.__process_video_subprocess,
                avg_color_frames = avg_color_frames,
                process_num = process_num,
                num_processes = num_processes,
                video_path = video_path
            ))

        # time.sleep(7)
        # video_player.playVideo(avg_color_frames, video_fps)
        for process in processes:
            process.wait()

        print("Processing whole video completed in " + str(round(time.time() - start, 2)) + " seconds.")

        self.__save_frames(avg_color_frames, video_fps)
        return avg_color_frames, video_fps

    def __get_avg_color_frame_shape(self):
        if self.__video_settings.is_color:
            return [self.__video_settings.display_width, self.__video_settings.display_height, 3]
        else:
            return [self.__video_settings.display_width, self.__video_settings.display_height]

    def __get_avg_color_frame(self, slice_width, slice_height, frame):
        avg_color_frame = np.empty(self.__get_avg_color_frame_shape(), np.uint8)
        for x in range(self.__video_settings.display_width):
            for y in range(self.__video_settings.display_height):
                mask = np.zeros(frame.shape[:2], np.uint8)
                start_y = int(round(y * slice_height, 0))
                end_y = int(round((y + 1) * slice_height, 0))

                start_x = int(round(x * slice_width, 0))
                end_x = int(round((x + 1) * slice_width, 0))

                mask[start_y:end_y, start_x:end_x] = 1

                # mean returns a list of four 0 - 255 values
                if (self.__video_settings.is_color):
                    mean = cv2.mean(frame, mask)
                    avg_color_frame[x, y, 0] = mean[0] # g
                    avg_color_frame[x, y, 1] = mean[1] # b
                    avg_color_frame[x, y, 2] = mean[2] # r
                else:
                    avg_color_frame[x, y] = cv2.mean(frame, mask)[0]

        return avg_color_frame

