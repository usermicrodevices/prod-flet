DESKTOP_FILE="$HOME/Desktop/kassa.desktop"
echo '[Desktop Entry]' > $DESKTOP_FILE
echo 'Name=kassa' >> $DESKTOP_FILE
echo 'Comment=prod kassa gui' >> $DESKTOP_FILE
echo 'Exec=/bin/bash -c "~/prod-flet/run_kassa.sh"' >> $DESKTOP_FILE
echo "Icon=$HOME/prod-flet/kassa.png" >> $DESKTOP_FILE
echo 'Terminal=false' >> $DESKTOP_FILE
echo 'Type=Application' >> $DESKTOP_FILE
echo 'Categories=Application;' >> $DESKTOP_FILE
gio set $DESKTOP_FILE metadata::trusted true
chmod a+x $DESKTOP_FILE
