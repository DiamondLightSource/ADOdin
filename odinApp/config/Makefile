TOP = ../..
include $(TOP)/configure/CONFIG

DATA += $(patsubst ../%, %, $(wildcard ../*.json))
DATA += $(patsubst ../%, %, $(wildcard ../*.xml))

include $(TOP)/configure/RULES
