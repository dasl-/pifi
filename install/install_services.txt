cd /home/pi/lightness/install
sudo chown root:root *.service
sudo chmod 644 *.service
sudo cp *.service /etc/systemd/system
sudo systemctl enable lightness*.service
sudo systemctl daemon-reload
sudo shutdown -r now
