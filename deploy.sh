#!/bin/bash

#GBLDIR=modules/comments/zcom/glbn/
#MCADIR=modules/comments/zcom/mcan/
#ESVDIR=modules/comments/zcom/esvn/

#generate OSIS
python studybible_to_osis.py --sword --osis esv.epub
unzip -o esv_module.zip -d ~/.sword/
python studybible_to_osis.py --sword --osis global.epub
unzip -o global_module.zip -d ~/.sword/
python studybible_to_osis.py --sword --osis mcarthur.epub
unzip -o mcarthur_module.zip -d ~/.sword/

#exit 0

#rm -r module_out
#mkdir module_out
#unzip -o esv_module.zip -d module_out
#unzip -o global_module.zip -d module_out
#unzip -o mcarthur_module.zip -d module_out
#
##rm -r module_out/modules/comments/zcom/*/images
#
##adb push module_out /sdcard/jsword
#
##exit 0
#
#ssh taandroid mkdir -p /sdcard/jsword/$ESVDIR
#ssh taandroid mkdir -p /sdcard/jsword/$MCADIR
#ssh taandroid mkdir -p /sdcard/jsword/$GBLDIR
#
#opts="-d -v --progress --delete"
#
#rsync $opts module_out/$ESVDIR/ taandroid:/sdcard/jsword/$ESVDIR/
#rsync $opts module_out/$GBLDIR/ taandroid:/sdcard/jsword/$GBLDIR/
#rsync $opts module_out/$MCADIR/ taandroid:/sdcard/jsword/$MCADIR/

#opts="-v -r --size-only --progress --delete"
#rsync $opts module_out/$ESVDIR/images/ taandroid:/sdcard/jsword/$ESVDIR/images/
#rsync $opts module_out/$GBLDIR/images/ taandroid:/sdcard/jsword/$GBLDIR/images/
#rsync $opts module_out/$MCADIR/images/ taandroid:/sdcard/jsword/$MCADIR/images/
#
#scp module_out/mods.d/*.conf taandroid:/sdcard/jsword/mods.d/
#ssh taandroid chmod -R 777 /sdcard/jsword

