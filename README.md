Study bibles into OSIS / sword modules BETA
===========================================

This script (study2sword.py) converts epub-type files into OSIS xml files, that can be further converted into
sword module.

Epub file for Global Study Bible (abreviated ESV study bible) can be downloaded for free from http://www.esv.org/e-books/.

Epub-files for ESV Study bible and McArthur Study Bible can be downloaded from crossway 
(https://www.crossway.org/customer/library/#product_type=Ebook) if you have purchased them either
as a physical book or only digitally. 

Installing and converting to sword module
-----------------------------------------

Install python packages beautifulsoup4 and jinja2:

pip install beautifulsoup4
pip install jinja2
pip install lxml

Unzip your epub file:

   mkdir modulename
   cd modulename
   unzip PATH_TO_MY.epub

Run command

python study2sword modulename

This will create OSIS XML file modulename.xml.

This can be converted to sword module by osis2mod tool, that can be obtained from
http://www.crosswire.org/wiki/DevTools:Modules

osis2mod module_dir/modules/comments/zcom/glbn/ esv.xml -v NRSV -z -b 4

Your sword module is now built under module_dir. Sample configurations are found in 
module_dir/mods.d/.

Quality considerations
----------------------
 - Only standard studynotes are included (no charts, figures etc)
 - Tested to work with xiphos. There seem to be problems currently with andbible, for example. Trying to fix that...

