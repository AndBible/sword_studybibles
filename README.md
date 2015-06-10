Study bibles into OSIS / sword modules BETA
===========================================

This script (study2sword.py) converts ePub-type files into OSIS xml files, that can be further converted into
sword module.

ePub file for Global Study Bible (abreviated ESV study bible) can be downloaded for free from http://www.esv.org/e-books/.

ePub-files for ESV Study Bible and McArthur Study Bible (and some other study bibles too)
can be downloaded from Crossway (https://www.crossway.org/customer/library/#product_type=Ebook) if you have purchased them either
as a physical book or only digitally. It is likely that other ePub bible commentaries can be handled by
this tool (if not directly, with smallish modifications to the code).

I'm proceeding to get free Global Study Bible module distributed via crosswire etc. and proprietary
modules via Crossway's e-library. At the moment I do not have rights to distribute any of them, but you
may use this tool to get your module.

Installing and converting to SWORD module
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

    python studybible_to_osis.py modulename

This will create OSIS XML file modulename.xml.

This can be converted to sword module by osis2mod tool, that can be obtained from
http://www.crosswire.org/wiki/DevTools:Modules

    osis2mod module_dir/modules/comments/zcom/glbn/ global.xml -v NRSV -z -b 4

Your sword module is now built under module_dir. Sample configurations are found in
module_dir/mods.d/.

Then copy figures from module_name/OEBPS/Images to module_dir/modules_comments/zcom/glbn/images/.

Quality considerations
----------------------
 - Studynotes, charts, figures etc
 - Tested with Andbible & Xiphos
 - Verse ranges fixed and links added

Known issues
------------
 - By default verse linking is hard-wired to ESVS module. This is to workaround with Andbible
   <reference> rendering bug (or feature - this is still to be disputed).

TODO
----
  - Add bible book intros into beginning of each book in commentary module
  - Make sword book module out of other articles
