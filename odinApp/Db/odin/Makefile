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

DB += OdinDetector.template
DB += OdinDataDriver.template
DB += OdinData.template
DB += MetaListener.template
DB += FrameProcessorPlugin.template
DB += SumPlugin.template
DB += OffsetAdjustmentPlugin.template
DB += ParameterAdjustmentPlugin.template
DB += UIDAdjustmentPlugin.template
DB += LiveViewPlugin.template
DB += BloscPlugin.template
DB += OdinProcServ.template

#----------------------------------------------------
# If <anyname>.db template is not named <anyname>*.template add
# <anyname>_template = <templatename>

include $(TOP)/configure/RULES
#----------------------------------------
#  ADD RULES AFTER THIS LINE

