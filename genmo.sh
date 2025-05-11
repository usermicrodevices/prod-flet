DOMAIN="prod"
INFNAME="$DOMAIN.po"
OUTFNAME="$DOMAIN.mo"

LOCALE=$1
if [[ -z $LOCALE ]]; then LOCALE=$(locale|grep LANGUAGE|cut -d= -f2|cut -d: -f1); fi

DIR="locale/$LOCALE/LC_MESSAGES"

INFILE="$DIR/$INFNAME"

OUTFILE="$DIR/$OUTFNAME"

[ -d $DIR ] || mkdir -p $DIR

msgfmt --directory=$DIR --output-file=$OUTFILE $INFNAME
