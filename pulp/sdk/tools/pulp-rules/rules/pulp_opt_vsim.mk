ifdef gui
override CONFIG_OPT += **/vsim/gui=true
endif

ifdef simchecker
override CONFIG_OPT += **/vsim/simchecker=true
endif

ifdef vsim/script
override CONFIG_OPT += **/vsim/script=$(vsim/script)
endif

help_opt_vsim:
	@echo
	@echo "Available make options for vsim platform:"
	@echo "  gui=1             Launch simulation from vsim GUI"
	@echo "  vsim/script=<path Specify path to a script used to launch the platform"
	@echo "  simchecker=1      Activate RISCV simchecker (ISA comparison against golden model)"
