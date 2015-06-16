Study bibles into OSIS / sword modules BETA
===========================================

This conversion utility is able to convert various bible commentary (study bible) ePub files
into SWORD modules. You must obtain ePub file (i.e. if e-book is being sold, you must buy it first).
 When you have the ePub file, you can use this utility to convert that file into a SWORD commentary module.

SWORD modules can be used with various Bible study software, including Xiphos on Linux/Windows desktop,
Eloquent for Apple OS X, AndBible on Android and Pocketsword on iPhone.

The following modules are tested to work:

 * The ESV Global Study Bible (download for free from ESV.org e-books).
 * The ESV Study Bible (buy from ESV.org e-books).
 * McArthur Study Bible (buy from ESV.org e-books).

Others ePub commentaries may work or not, but feel free to try out. Support for other ePub commentary books can be
suggested via Github issue or by email. This software is at beta stage.

Online version
----------------

Try ONLINE version at http://tuomasairaksinen.fi/studybibles/

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
