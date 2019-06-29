# lightness
## About
[todo]

## Setting up from Scratch
### Install Raspian Stretch Lite
https://www.raspberrypi.org/documentation/installation/installing-images/mac.md
1. `diskutil list`
1. `diskutil unmountDisk /dev/disk<disk# from diskutil>`
1. `sudo dd bs=1m if=image.img of=/dev/rdisk<disk# from diskutil> conv=sync`

### Set up Wifi
wpa_supplicant.conf:

    country=US
    ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
    update_config=1
    network={
      ssid="MyWiFiNetwork"
      psk="MyPassword"
      key_mgmt=WPA-PSK
    }

### Enable ssh, Connect
1. `touch ssh`
1. plug in raspberry pi
1. find its IP: `sudo arp-scan --interface=en0 --localnet`
1. ssh in (u/p:pi/raspberry)

### Setup Raspberry Pi
1. `sudo raspi-config`
-- change password
-- enable SPI (interfacing options)
1. `sudo apt-get update`
1. `sudo apt-get upgrade -y`
1. `sudo apt-get install git`

### Setup Git
1. `ssh-keygen -t rsa -b 4096 -C “your@email.com”`
1. `eval "$(ssh-agent -s)"`
1. `ssh-add ~/.ssh/id_rsa`
1. `more ~/.ssh/id_rsa.pub` (copy to git)

### Checkout Repo
1. `git clone git@github.com:dasl-/lightness.git`
1. `cd lightness`

### Install Dependencies
1. `sh dependencies.sh`

### Connect GPIO Pins
(pinout: https://pinout.xyz/)
- power: 2
- ground: 6
- data: 19
- clock: 23

### Copy Adafruit LED Drivers
(from https://github.com/adafruit/Adafruit_Python_GPIO)
1. `cd ~`
1. `git clone https://github.com/adafruit/Adafruit_Python_GPIO.git`
1. `cd Adafruit_Python_GPIO`
1. `sudo python setup.py install`

### Set Up Sublime
1. `sudo wget -O /usr/local/bin/subl https://raw.github.com/aurora/rmate/master/rmate`
1. `sudo chmod a+x /usr/local/bin/subl`
