TOP=../../..
include $(TOP)/configure/CONFIG
#----------------------------------------
#  ADD MACRO DEFINITIONS AFTER THIS LINE

#----------------------------------------------------
#  Optimization of db files using dbst (DEFAULT: NO)
#DB_OPT = YES

#----------------------------------------------------
# Create and install (or just install)
# databases, templates, substitutions like this

DB += ExcaliburDetector.template
DB += ExcaliburFemHousekeeping.template
DB += Excalibur2FemStatus.template
DB += Excalibur6FemStatus.template
DB += ExcaliburFemStatus.template
DB += ExcaliburOD.template
DB += ExcaliburODMode.template
DB += Excalibur1NodeOD.template
DB += Excalibur2NodeOD.template
DB += Excalibur4NodeOD.template
DB += Excalibur8NodeOD.template

#----------------------------------------------------
# If <anyname>.db template is not named <anyname>*.template add
# <anyname>_template = <templatename>

include $(TOP)/configure/RULES
#----------------------------------------
#  ADD RULES AFTER THIS LINE

