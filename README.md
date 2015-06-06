Study bibles into OSIS / sword modules BETA
===========================================

This script (study2sword.py) converts epub-type files into OSIS xml files, that can be further converted into
sword module.

Epub file for Global Study Bible (abreviated ESV study bible) can be downloaded for free from http://www.esv.org/e-books/.

Epub-files for ESV Study bible and McArthur Study Bible can be downloaded from crossway 
(https://www.crossway.org/customer/library/#product_type=Ebook) if you have purchased them either
as a physical book or only digitally. 

I'm proceeding to get free Global Study Bible module distributed via crosswire etc. and proprietary
modules via crossway's e-library.

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
 - Studynotes, charts, figures etc OK
 - Tested with Andbible & Xiphos - OK

Known issues
------------
 - Andbible issue: verse links when there is verse range do not show correctly.
 - If comment is for verse range, it is actually shown only for the first verse (all apps).

TODO
----
  - Add bible book intros into beginning of each book in commentary module
  - Make sword book module out of other articles