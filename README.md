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

Online version
----------------

If playing around with python scripts is not your thing, you may use my easy
online version here:

*coming soon*


Installing and converting to SWORD module
-----------------------------------------

Install some python packages:

    pip install beautifulsoup4
    pip install jinja2
    pip install lxml

Install osis2mod tool that can be obtained from http://www.crosswire.org/wiki/DevTools:Modules

To convert ePub to SWORD module (compressed in a zip file), run command

    python studybible_to_osis.py your_book.epub your_module.zip --sword

Quality considerations
----------------------
 - Studynotes, charts, figures etc
 - Tested with Andbible & Xiphos
 - Verse ranges fixed and links added

Known issues
------------
 - By default verse linking is hard-wired to ESVS module. This is to workaround with Andbible
   <reference> rendering bug (or feature - this is still to be disputed).
   You may use --bible_work_id None if you wish not to use ESVS as your bible.

TODO
----
  - Add bible book intros into beginning of each book in commentary module (+ backreferences)
  - Make sword book module out of other articles
