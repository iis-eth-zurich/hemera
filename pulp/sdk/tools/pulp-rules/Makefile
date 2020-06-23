define declareInstallFile

$(PULP_SDK_INSTALL)/$(1): $(1)
	install -D $(1) $$@

INSTALL_HEADERS += $(PULP_SDK_INSTALL)/$(1)

endef


INSTALL_FILES += $(shell find rules -name *.mk)

$(foreach file, $(INSTALL_FILES), $(eval $(call declareInstallFile,$(file))))

all: $(INSTALL_HEADERS)