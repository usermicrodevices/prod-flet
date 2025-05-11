DOMAIN="prod"
OUTFNAME="$DOMAIN.po"

LOCALE=$1
if [[ -z $LOCALE ]]; then LOCALE=$(locale|grep LANGUAGE|cut -d= -f2|cut -d: -f1); fi

DIR="locale/$LOCALE/LC_MESSAGES"

OUTFILE="$DIR/$OUTFNAME"

SRCFILES=$(find src/ -name "*.py")

[ -d $DIR ] || mkdir -p $DIR

{ [ -e $OUTFILE ] || touch $OUTFILE; } && ! [ -w $OUTFILE ] && echo "cannot write to $OUTFILE" && exit 1

. ./venv/bin/activate

python src/third_party/pygettext.py --default-domain=$DOMAIN --output-dir=$DIR --output=$OUTFNAME --no-location $SRCFILES
