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

# running
```
flet src/main.py
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
