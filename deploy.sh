#!/bin/bash

GBLDIR=modules/comments/zcom/glbn/
MCADIR=modules/comments/zcom/mcan/
ESVDIR=modules/comments/zcom/esvn/

#generate OSIS
python study2sword/study2sword.py --title "The ESV Study Bible notes" --work_id "ESVN" esv --tag_level 0
python study2sword/study2sword.py --title "The ESV Global Study Bible notes" --work_id "GLBN" global --tag_level 0
python study2sword/study2sword.py --title "The McArthur Study Bible notes" --work_id "MCAN" mcarthur --tag_level 0

mkdir module_dir/$ESVDIR
mkdir module_dir/$MCADIR
mkdir module_dir/$GBLDIR

rm module_dir/$ESVDIR/*
rm module_dir/$MCADIR/*
rm module_dir/$GBLDIR/*

# convert into sword module
osis2mod module_dir/$ESVDIR esv.xml -v NRSV -z -b 3 > /dev/null
osis2mod module_dir/$GBLDIR global.xml -v NRSV -z -b 3 > /dev/null
osis2mod module_dir/$MCADIR mcarthur.xml -v NRSV -z -b 3 > /dev/null

#install locally
rm -r ~/.sword/$ESVDIR
rm -r ~/.sword/$MCADIR
rm -r ~/.sword/$GBLDIR
mkdir ~/.sword/$ESVDIR
mkdir ~/.sword/$MCADIR
mkdir ~/.sword/$GBLDIR

cp -r module_dir/$ESVDIR/* ~/.sword/$ESVDIR/
cp -r module_dir/$MCADIR/* ~/.sword/$MCADIR/
cp -r module_dir/$GBLDIR/* ~/.sword/$GBLDIR/

cp module_dir/mods.d/*.conf ~/.sword/mods.d/
#exit 0
#android
ssh taandroid mkdir /sdcard/jsword/$ESVDIR
ssh taandroid mkdir /sdcard/jsword/$MCADIR
ssh taandroid mkdir /sdcard/jsword/$GBLDIR

#ssh taandroid rm -r /sdcard/jsword/$ESVDIR/*
#ssh taandroid rm /sdcard/jsword/$MCADIR/*
#ssh taandroid rm /sdcard/jsword/$GBLDIR/*

opts="-t -v -r --progress --delete"

rsync $opts module_dir/$ESVDIR/ taandroid:/sdcard/jsword/$ESVDIR/
rsync $opts module_dir/$GBLDIR/ taandroid:/sdcard/jsword/$GBLDIR/
rsync $opts module_dir/$MCADIR/ taandroid:/sdcard/jsword/$MCADIR/

scp module_dir/mods.d/*.conf taandroid:/sdcard/jsword/mods.d/
ssh taandroid chmod -R 777 /sdcard/jsword

#generate global.zip for distributon
rm -r global_dir
cp -r module_dir global_dir
rm global_dir/mods.d/esvn.conf
rm global_dir/mods.d/mcan.conf
rm -r global_dir/modules/comments/zcom/mcan
rm -r global_dir/modules/comments/zcom/esvn
cd global_dir
zip -r glbn.zip *