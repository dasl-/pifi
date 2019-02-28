import numpy as np
import cv2
import pafy
import pprint
import random
import time
import argparse

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
    parser.add_argument('--skip-frames', dest='skip_frames', action='store', type=int, default=0, metavar='N',
        help='Number of frames to skip every output iteration from the youtube video. Default: 0')
    parser.add_argument('--color', dest='is_color', action='store_true', default=False,
        help='color output? (default is black and white)')

    args = parser.parse_args()
    return args

def setupOutputPi():
    from driver import apa102
    pixels = apa102.APA102(num_led=240, global_brightness=10, mosi = 10, sclk = 11, order='rbg')
    pixels.clear_strip()
    return pixels

def showOutputPi(output):
    for x in range(args.display_width):
        for y in range(args.display_height):
            if args.is_color:
                r = scaleOutput(output[x, y, 2])
                b = scaleOutput(output[x, y, 1])
                g = scaleOutput(output[x, y, 0])
                color = pixels.combine_color(r, g, b)
            else:
                grayscale = scaleOutput(output[x, y])
                color = pixels.combine_color(grayscale, grayscale, grayscale)
            pixels.set_pixel_rgb(x + (y * args.display_width), color)
    pixels.show()

def scaleOutput(val):
    return int(val / 10)

def showOutputFrame(output): #todo: fix this for running with --color
    canvas_width = 600
    canvas_height = 400

    img = np.zeros((canvas_height, canvas_width, 1), np.uint8)
    slice_height = int(canvas_height / args.display_height)
    slice_width = int(canvas_width / args.display_width)
    for x in range(args.display_width):
        for y in range(args.display_height):
            img[(y * slice_height):((y + 1) * slice_height), (x * slice_width):((x + 1) * slice_width)] = output[x, y]

    cv2.imshow('image',img)
    cv2.waitKey(1)

def getVideo():
    p = pafy.new(args.url)
    video = p.getbest()
    print(p.videostreams)

    # pick lowest resolution because it will be less resource intensive to process
    lowest_res_stream = None
    lowest_x_dimension = None
    for stream in p.videostreams:
        if not lowest_res_stream or stream.dimensions[0] < lowest_x_dimension:
            lowest_res_stream = stream
            lowest_x_dimension = stream.dimensions[0]

    return lowest_res_stream


args = parseArgs()
pixels = None
if (args.should_output_pi):
    pixels = setupOutputPi()

video = getVideo()

# start the video
cap = cv2.VideoCapture(video.url)
while (True):
    for x in range(args.skip_frames + 1):
        cap.grab()
    ret, frame = cap.retrieve()

    if (not args.is_color):
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

    frame_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    frame_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

    slice_height = int(frame_height / args.display_height)
    slice_width = int(frame_width / args.display_width)

    if (args.is_color):
        output = np.zeros((args.display_width, args.display_height, 3), np.uint8)
    else:
        output = np.zeros((args.display_width, args.display_height), np.uint8)

    for x in range(args.display_width):
        for y in range(args.display_height):
            mask = np.zeros(frame.shape[:2], np.uint8)
            mask[(y * slice_height):((y + 1) * slice_height), (x * slice_width):((x + 1) * slice_width)] = 1
            # mean returns a list of four 0 - 255 values
            if (args.is_color):
                mean = cv2.mean(frame, mask)
                output[x, y, 0] = mean[0]
                output[x, y, 1] = mean[1]
                output[x, y, 2] = mean[2]
            else:
                output[x, y] = cv2.mean(frame, mask)[0]

    print(cap.get(cv2.CAP_PROP_POS_MSEC))
    print(frame.shape)
    pprint.pprint(output)

    if args.should_output_pi:
        showOutputPi(output)

    if args.should_output_frame:
        showOutputFrame(output)

cap.release()
cv2.destroyAllWindows()
