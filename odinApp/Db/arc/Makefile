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

DB += ArcDetector.template
DB += Arc1NodeOD.template
DB += Arc2NodeOD.template
DB += Arc4NodeOD.template
DB += ArcOD.template
DB += ArcODMode.template
DB += Arc1FemStatus.template
DB += Arc2FemStatus.template
DB += ArcFemStatus.template
DB += Arc1FemHousekeeping.template
DB += Arc2FemHousekeeping.template
DB += ArcBaseFemHousekeeping.template

#----------------------------------------------------
# If <anyname>.db template is not named <anyname>*.template add
# <anyname>_template = <templatename>

include $(TOP)/configure/RULES
#----------------------------------------
#  ADD RULES AFTER THIS LINE

