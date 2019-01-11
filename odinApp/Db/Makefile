TOP = ../..
include $(TOP)/configure/CONFIG

DIRS := $(DIRS) odin
DIRS := $(DIRS) eiger
DIRS := $(DIRS) excalibur
#----------------------------------------------------
#  Optimization of db files using dbst (DEFAULT: NO)
#DB_OPT = YES

#----------------------------------------------------
# Create and install (or just install)
# databases, templates, substitutions like this

DB += TristanDetector.template
DB += TristanStatus.template
DB += TristanFemStatus.template
DB += Tristan1MStatus.template
DB += Tristan10MStatus.template
DB += TristanOD.template
DB += Tristan4NodeOD.template
DB += Tristan8NodeOD.template

#----------------------------------------------------
# If <anyname>.db template is not named <anyname>*.template add
# <anyname>_template = <templatename>

#----------------------------------------
#  ADD RULES AFTER THIS LINE
include $(TOP)/configure/RULES
include $(TOP)/configure/RULES_DIRS