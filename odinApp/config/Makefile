TOP = ../..
include $(TOP)/configure/CONFIG

DATA += $(patsubst ../%, %, $(wildcard ../*startup))
DATA += $(patsubst ../%, %, $(wildcard ../*.ini))
DATA += $(patsubst ../%, %, $(wildcard ../*.json))
DATA += $(patsubst ../%, %, $(wildcard ../*.xml))

include $(TOP)/configure/RULES
