#!/usr/bin/python3
import numpy as np
import cv2
import pafy
import pprint
import random
import time
import argparse
import math
import os
import time
import keyboard
import sys

import videoplayer
import settings

def parseArgs():
    parser = argparse.ArgumentParser(description='convert a video.')
    parser.add_argument('--url', dest='url', action='store', default='https://www.youtube.com/watch?v=xmUZ6nCFNoU',
        help='youtube video url. default: The Smashing Pumpkins - Today.')
    parser.add_argument('--out-pi', dest='should_output_pi', action='store_true', default=False,
        help='Display output on raspberry pi.')
    parser.add_argument('--out-frame', dest='should_output_frame', action='store_true', default=False,
        help='Display output on opencv frame.')
    parser.add_argument('--display-width', dest='display_width', action='store', type=int, default=19, metavar='N',
        help='Number of pixels / units')
    parser.add_argument('--display-height', dest='display_height', action='store', type=int, default=4, metavar='N',
        help='Number of pixels / units')
    parser.add_argument('--skip-frames', dest='num_skip_frames', action='store', type=int, default=0, metavar='N',
        help='Number of frames to skip every output iteration from the youtube video. Default: 0 (skip no frames)')
    parser.add_argument('--color', dest='is_color', action='store_true', default=False,
        help='color output? (default is black and white)')
    parser.add_argument('--brightness', dest='brightness', action='store', type=int, default=3, metavar='N',
        help='Global brightness value. Max of 31.')
    parser.add_argument('--stream', dest='should_preprocess_video', action='store_false', default=True,
        help='If set, the video will be streamed instead of pre-processed')

    args = parser.parse_args()
    return args

def get_video_stream(should_preprocess_video):
    p = pafy.new(args.url)

    # pick lowest resolution because it will be less resource intensive to process
    best_stream = None
    lowest_x_dimension = None

    print("Options:")
    for stream in p.videostreams:
        print("    " + stream.extension + "@" + stream.resolution + " " +
            str(stream._info['fps']) + "fps " + str(round(stream._info['filesize']/1024/1024, 2)) + "MB")
        if (not best_stream or
            (
                stream.dimensions[0] <= lowest_x_dimension and
                stream.extension == 'webm' # prefer webm because mp4s sometimes refuse to play
            )
        ):
            best_stream = stream
            lowest_x_dimension = stream.dimensions[0]
    print("Using: " + str(best_stream))
    pprint.pprint(best_stream.__dict__)
    return best_stream

def save_frames(video_stream, avg_color_frames, is_color, num_skip_frames, fps):
    np.save(get_frames_save_path(video_stream, is_color, num_skip_frames), [fps, avg_color_frames])

def get_frames_save_path(video_stream, is_color, num_skip_frames):
    save_dir = sys.path[0] + "/lightness_data"
    os.makedirs(save_dir, exist_ok = True)
    color_str = ""
    if is_color:
        color_str += "color"
    else:
        color_str += "bw"
    save_path = (save_dir + "/" + video_stream.title + "@" + video_stream.resolution + "__" + color_str +
        "__skip" + str(num_skip_frames) + "." + video_stream.extension + ".npy")
    return save_path

# download video rather than streaming to avoid errors like:
# [tls @ 0x1388940] Error in the pull function.
# [matroska,webm @ 0x1396ff0] Read error
# [tls @ 0x1388940] The specified session has been invalidated for some reason.
# [tls @ 0x1388940] The specified session has been invalidated for some reason.
def download_video(video_stream):
    save_dir = sys.path[0] + "/lightness_data"
    os.makedirs(save_dir, exist_ok = True)

    save_path = save_dir + "/" + video_stream.title + "@" + video_stream.resolution + "." + video_stream.extension
    print("video path: " + save_path)
    if not os.path.exists(save_path):
        video_stream.download(save_path)
    return save_path


def get_next_frame(vid_cap, num_skip_frames):
    success = True
    for x in range(num_skip_frames + 1): # add one because we need to call .grab() once even if we're skipping no frames.
        success = vid_cap.grab()
        if not success:
            return False, None
    success, frame = vid_cap.retrieve()
    if not success:
        return False, None
    return success, frame

def process_video(video_stream, args):
    video_path = download_video(video_stream)

    # start the video
    vid_cap = cv2.VideoCapture(video_path)

    fps = vid_cap.get(cv2.CAP_PROP_FPS)
    avg_color_frames = []
    start = time.time()
    while (True):
        success, frame = get_next_frame(vid_cap, args.num_skip_frames)
        if not success:
            break

        if not args.is_color:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)


        frame_width = vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        frame_height = vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

        slice_height = (frame_height / args.display_height)
        slice_width = (frame_width / args.display_width)

        if args.is_color:
            avg_color_frame = np.zeros((args.display_width, args.display_height, 3), np.uint8)
        else:
            avg_color_frame = np.zeros((args.display_width, args.display_height), np.uint8)

        for x in range(args.display_width):
            for y in range(args.display_height):
                mask = np.zeros(frame.shape[:2], np.uint8)
                start_y = int(round(y * slice_height, 0))
                end_y = int(round((y + 1) * slice_height, 0))

                start_x = int(round(x * slice_width, 0))
                end_x = int(round((x + 1) * slice_width, 0))

                mask[start_y:end_y, start_x:end_x] = 1

                # mean returns a list of four 0 - 255 values
                if (args.is_color):
                    mean = cv2.mean(frame, mask)
                    avg_color_frame[x, y, 0] = mean[0] # g
                    avg_color_frame[x, y, 1] = mean[1] # b
                    avg_color_frame[x, y, 2] = mean[2] # r
                else:
                    avg_color_frame[x, y] = cv2.mean(frame, mask)[0]

        print(vid_cap.get(cv2.CAP_PROP_POS_MSEC))
        print(frame.shape)
        print(vid_cap.get(cv2.CAP_PROP_FPS))
        #pprint.pprint(avg_color_frame)

        if args.should_preprocess_video:
            avg_color_frames.append(avg_color_frame)
        else:
            video_player.playFrame(avg_color_frame)

    end = time.time()
    print("processing video took: " + str(end - start) + " seconds")
    vid_cap.release()
    if args.should_preprocess_video:
        save_frames(video_stream, avg_color_frames, args.is_color, args.num_skip_frames, fps)
        video_player.playVideo(avg_color_frames, fps)

args = parseArgs()

video_settings = settings.Settings(args)

video_player = videoplayer.VideoPlayer(video_settings)
video_stream = get_video_stream(args.should_preprocess_video)
frames_save_path = get_frames_save_path(video_stream, args.is_color, args.num_skip_frames)
print("frames path: " + frames_save_path)

if os.path.exists(frames_save_path):
    fps, avg_color_frames = np.load(frames_save_path)

    video_player.playVideo(avg_color_frames, fps)
else:
    process_video(video_stream, args)

cv2.destroyAllWindows()