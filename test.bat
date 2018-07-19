@echo off

set ip=%1
set file=%2
set location=%3

tftp -i %ip% put %file% %location%
