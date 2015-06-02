rm esvstudy/modules/comments/zcom/esvstudy/*
osis2mod esvstudy/modules/comments/zcom/esvstudy/ out.osis -v NRSV -z -b 4
#rm ~/.sword/esvstudy.zip
#zip -r ~/.sword/esvstudy.zip esvstudy/
#cd ~/.sword
#unzip esvstudy.zip
rm ~/.sword/modules/comments/zcom/esvstudy/*
cp esvstudy/modules/comments/zcom/esvstudy/* ~/.sword/modules/comments/zcom/esvstudy/
scp -r esvstudy/modules/comments/zcom/esvstudy/ taandroid:/sdcard/jsword/modules/comments/zcom/esvstudy/
scp esvstudy/mods.d/esvstudy.conf taandroid:/sdcard/jsword/mods.d/
cp esvstudy/mods.d/esvstudy.conf ~/.sword/mods.d/
ssh taandroid chmod -R 777 /sdcard/jsword