TOP = ..
include $(TOP)/configure/CONFIG

DIRS := $(DIRS) src
DIRS := $(DIRS) frozenSrc
src_DEPEND_DIRS += frozenSrc
DIRS := $(DIRS) $(filter-out $(DIRS), $(wildcard *db*))
DIRS := $(DIRS) $(filter-out $(DIRS), $(wildcard *Db*))
DIRS := $(DIRS) $(filter-out $(DIRS), $(wildcard op*))

include $(TOP)/configure/RULES_DIRS
