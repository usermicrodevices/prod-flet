# prod-flet
frontend for ["prod"](https://github.com/usermicrodevices/prod/) (warehouse system management based on [Django](https://github.com/django/django)). client developed in [Flet (it is Python wraper arount Flutter)](https://github.com/flet-dev/flet)

[![badge](https://img.shields.io/badge/license-MIT-blue)](https://github.com/usermicrodevices/prod/blob/main/LICENSE)

![image](./screen.png "main screen")
![image](./phone-screen.jpg "main screen")

# installation
```
git clone git@github.com:usermicrodevices/prod-flet.git
cd prod-flet
python -m venv venv
. ./venv/bin/activate
pip install .
```

# fix ubuntu run missing dependencies
```
sudo apt update
sudo apt install libmpv-dev libmpv2
sudo ln -s /usr/lib/x86_64-linux-gnu/libmpv.so /usr/lib/libmpv.so.1
```

# running
```
flet run src/main.py
```

# build android
```
flet build apk
```

# build linux
```
flet build linux
```

# build windows
```
flet build windows
```

# pack as standalone executable file
```
pip install pyinstaller
flet pack --icon kassa.png --name prod-flet src/main.py
```

# generate desktop and autostart files in linux Ubuntu for Gnome Desktop
```
sudo apt install gnome-startup-applications
./gen_desk.sh
```


# add linux user group "dialout" for read and write serial port
first check serial group
```
ls -la /dev/ttyS0
```
or
```
ls -la /dev/ttyUSB0
```
view like ```crw-rw---- 1 root dialout 188, 0 мар 30 06:18 /dev/ttyUSB0```
and next add group
```
sudo usermod -a -G dialout $USER
```


# if set "dialout" group not help, set linux permissions for read and write serial port for any user
```
sudo chmod a+rw /dev/ttyS0
```
or
```
sudo chmod a+rw /dev/ttyUSB0
```
