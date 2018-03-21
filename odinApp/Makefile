TOP = ..
include $(TOP)/configure/CONFIG

DIRS := $(DIRS) src
DIRS := $(DIRS) $(filter-out $(DIRS), $(wildcard *db*))
DIRS := $(DIRS) $(filter-out $(DIRS), $(wildcard *Db*))
DIRS := $(DIRS) $(filter-out $(DIRS), $(wildcard op*))
DIRS := $(DIRS) $(filter-out $(DIRS), $(wildcard config))

include $(TOP)/configure/RULES_DIRS
