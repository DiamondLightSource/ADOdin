TOP = ../../..
include $(TOP)/configure/CONFIG
#----------------------------------------
#  ADD MACRO DEFINITIONS AFTER THIS LINE

#----------------------------------------------------
#  Optimization of db files using dbst (DEFAULT: NO)
#DB_OPT = YES

#----------------------------------------------------
# Create and install (or just install)
# databases, templates, substitutions like this

DB += TristanDetector.template
DB += TristanStatus.template
DB += Tristan1MStatus.template
DB += Tristan2MStatus.template
DB += Tristan10MStatus.template
DB += TristanOD.template
DB += Tristan4NodeOD.template
DB += Tristan8NodeOD.template
DB += Tristan16NodeOD.template

#----------------------------------------------------
# If <anyname>.db template is not named <anyname>*.template add
# <anyname>_template = <templatename>

include $(TOP)/configure/RULES
#----------------------------------------
#  ADD RULES AFTER THIS LINE
