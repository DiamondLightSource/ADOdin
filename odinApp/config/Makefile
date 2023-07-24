TOP = ../..
include $(TOP)/configure/CONFIG

DATA += $(patsubst ../%, %, $(wildcard ../*startup))
DATA += $(patsubst ../%, %, $(wildcard ../*.ini))
DATA += $(patsubst ../%, %, $(wildcard ../*.json))
DATA += $(patsubst ../%, %, $(wildcard ../*.xml))
DATA += $(patsubst ../%, %, $(wildcard ../*.yaml))
DATA += $(patsubst ../%, %, $(wildcard ../*.kdl))
DATA += $(patsubst ../%, %, $(wildcard ../*.sh))

include $(TOP)/configure/RULES
