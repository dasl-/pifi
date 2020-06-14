### Setting up sublime via rmate:
1. `sudo wget -O /usr/local/bin/subl https://raw.github.com/aurora/rmate/master/rmate`
1. `sudo chmod a+x /usr/local/bin/subl`

### Setting up sublime with sftp:
This is another option. This rsync script will be useful to sync the remote pi copy with your local copy. Run it from your local machine. Modify as appropriate for your directory structure, IP address etc.:
```
rsync -avz --delete --exclude '*.swp' --exclude '.git' --exclude '.tags' --exclude '*.jar' \
  --exclude '*.class' --exclude '*.md5' --exclude '*.sha1' --exclude '*.zip' \
  --exclude '.project' --exclude '.DS_Store' --exclude '*.gem' --exclude '*.gz' \
  --exclude 'vendor/gems' --exclude '*.a' --exclude '*.so' --exclude '*.so.*' \
  --exclude '*.la' --exclude 'sftp-config.json' --exclude '.idea' --exclude '*.db' \
  --exclude '*.rpm' --exclude '*.sqlite' --exclude '*.tsv' --exclude 'node_modules/' --exclude 'build/' \
  --exclude 'data/' --exclude '__pycache__/' --exclude '*.npy' \
  pi@192.168.1.100:~/development/ ~/pi/development
```
