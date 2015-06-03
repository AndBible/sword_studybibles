#!/bin/bash

GBLDIR=modules/comments/zcom/glbn/
MCADIR=modules/comments/zcom/mcan/
ESVDIR=modules/comments/zcom/esvn/

#generate OSIS
python study2sword.py --title "ESV Global Study Bible Notes" --work_id "GBLN" global
python study2sword.py --title "McArthur Study Bible Notes" --work_id "MCAN" mcarthur
python study2sword.py --title "ESV Study Bible Notes" --work_id "ESVN" esv

mkdir module_dir/$ESVDIR
mkdir module_dir/$MCADIR
mkdir module_dir/$GBLDIR

rm module_dir/$ESVDIR/*
rm module_dir/$MCADIR/*
rm module_dir/$GBLDIR/*

# convert into sword module
osis2mod module_dir/$ESVDIR esv.xml -v NRSV -z -b 4
osis2mod module_dir/$GBLDIR global.xml -v NRSV -z -b 4
osis2mod module_dir/$MCADIR mcarthur.xml -v NRSV -z -b 4

#install locally
rm -r ~/.sword/$ESVDIR
rm -r ~/.sword/$MCADIR
rm -r ~/.sword/$GBLDIR
mkdir ~/.sword/$ESVDIR
mkdir ~/.sword/$MCADIR
mkdir ~/.sword/$GBLDIR

cp module_dir/$ESVDIR/* ~/.sword/$ESVDIR/
cp module_dir/$MCADIR/* ~/.sword/$MCADIR/
cp module_dir/$GBLDIR/* ~/.sword/$GBLDIR/

cp module_dir/mods.d/*.conf ~/.sword/mods.d/

#android
ssh taandroid mkdir /sdcard/jsword/$ESVDIR
ssh taandroid mkdir /sdcard/jsword/$MCADIR
ssh taandroid mkdir /sdcard/jsword/$GBLDIR

ssh taandroid rm /sdcard/jsword/$ESVDIR/*
ssh taandroid rm /sdcard/jsword/$MCADIR/*
ssh taandroid rm /sdcard/jsword/$GBLDIR/*

scp -r module_dir/$ESVDIR/ taandroid:/sdcard/jsword/$ESVDIR/
scp -r module_dir/$GBLDIR/ taandroid:/sdcard/jsword/$GBLDIR/
scp -r module_dir/$MCADIR/ taandroid:/sdcard/jsword/$MCADIR/

scp module_dir/mods.d/*.conf taandroid:/sdcard/jsword/mods.d/
ssh taandroid chmod -R 777 /sdcard/jsword
