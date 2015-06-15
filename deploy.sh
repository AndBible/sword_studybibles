#!/bin/bash

GBLDIR=modules/comments/zcom/glbn/
MCADIR=modules/comments/zcom/mcan/
ESVDIR=modules/comments/zcom/esvn/

#generate OSIS
python studybible_to_osis.py --title "The ESV Study Bible notes" --work_id "ESVN" esv.epub --tag_level 0 --sword
unzip -o esv_module.zip -d ~/.sword/
python studybible_to_osis.py --title "The ESV Global Study Bible notes" --work_id "GLBN" global.epub --tag_level 0 --sword
unzip -o global_module.zip -d ~/.sword/
python studybible_to_osis.py --title "The McArthur Study Bible notes" --work_id "MCAN" mcarthur.epub --tag_level 0 --sword
unzip -o mcarthur_module.zip -d ~/.sword/

#exit 0

rm -r module_out
mkdir module_out
unzip esv_module.zip -d module_out
unzip global_module.zip -d module_out
unzip mcarthur_module.zip -d module_out
ssh taandroid mkdir /sdcard/jsword/$ESVDIR
ssh taandroid mkdir /sdcard/jsword/$MCADIR
ssh taandroid mkdir /sdcard/jsword/$GBLDIR

opts="-v -r --progress --delete"

rsync $opts module_out/$ESVDIR/ taandroid:/sdcard/jsword/$ESVDIR/
rsync $opts module_out/$GBLDIR/ taandroid:/sdcard/jsword/$GBLDIR/
rsync $opts module_out/$MCADIR/ taandroid:/sdcard/jsword/$MCADIR/

scp module_out/mods.d/*.conf taandroid:/sdcard/jsword/mods.d/
ssh taandroid chmod -R 777 /sdcard/jsword

