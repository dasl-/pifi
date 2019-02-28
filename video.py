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

    args = parser.parse_args()
    return args

def setupOutputPi():
    import board
    import neopixel
    num_pixels = args.display_width * args.display_height
    pixels = neopixel.NeoPixel(board.D18, num_pixels)
    return pixels

def showOutputPi(grayscale_output):
    for x in range(args.display_width):
        for y in range(args.display_height):
            val = int(grayscale_output[x,y] / 4)
            pixels[x + (y * args.display_width)] = (val, val, val)
    pixels.show()

def showOutputFrame(grayscale_output):
    canvas_width = 600
    canvas_height = 400

    img = np.zeros((canvas_height, canvas_width, 1), np.uint8) * random.randint(1,255)
    slice_height = int(canvas_height / args.display_height)
    slice_width = int(canvas_width / args.display_width)
    for x in range(args.display_width):
        for y in range(args.display_height):
            img[(y * slice_height):((y + 1) * slice_height), (x * slice_width):((x + 1) * slice_width)] = grayscale_output[x, y]

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
    ret, frame = cap.read()
    # for x in range(1000):
    #     cap.grab()
    # ret, frame = cap.retrieve()
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

    frame_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    frame_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

    slice_height = int(frame_height / args.display_height)
    slice_width = int(frame_width / args.display_width)

    grayscale_output = np.zeros((args.display_width, args.display_height), np.uint8)
    for x in range(args.display_width):
        for y in range(args.display_height):
            mask = np.zeros(frame.shape, np.uint8)
            mask[(y * slice_height):((y + 1) * slice_height), (x * slice_width):((x + 1) * slice_width)] = 1
            slice_grayscale = cv2.mean(frame, mask)[0] # 0 - 255 value
            grayscale_output[x, y] = slice_grayscale

    print(cap.get(cv2.CAP_PROP_POS_MSEC))
    print(frame.shape)
    pprint.pprint(grayscale_output)

    if args.should_output_pi:
        showOutputPi(grayscale_output)

    if args.should_output_frame:
        showOutputFrame(grayscale_output)

cap.release()
cv2.destroyAllWindows()