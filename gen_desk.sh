DESKTOP_DIR="$HOME/Desktop"
DESKTOP_FILE="$DESKTOP_DIR/kassa.desktop"
AUTOSTART_DIR="$HOME/.config/autostart"
AUTOSTART_FILE="$AUTOSTART_DIR/kassa.desktop"

if [ ! -d $DESKTOP_DIR ]; then
 mkdir $DESKTOP_DIR
fi
echo '[Desktop Entry]' > $DESKTOP_FILE
echo 'Name=kassa' >> $DESKTOP_FILE
echo 'Comment=prod kassa gui' >> $DESKTOP_FILE
echo 'Exec=/bin/bash -c "~/prod-flet/run_kassa.sh"' >> $DESKTOP_FILE
echo "Icon=$HOME/prod-flet/kassa.png" >> $DESKTOP_FILE
echo 'Terminal=false' >> $DESKTOP_FILE
echo 'Type=Application' >> $DESKTOP_FILE
echo 'Categories=Application;' >> $DESKTOP_FILE
gio set $DESKTOP_FILE metadata::trusted true
chmod u+x $DESKTOP_FILE

if [ ! -d $AUTOSTART_DIR ]; then
 mkdir $AUTOSTART_DIR
fi
cp $DESKTOP_FILE $AUTOSTART_FILE
echo 'X-GNOME-Autostart-enabled=true' >> $AUTOSTART_FILE
