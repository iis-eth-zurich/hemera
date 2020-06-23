ifdef rt/no-werror
override CONFIG_OPT += **/rt/werror=false
endif

ifdef rt/mode
ifeq '$(rt/mode)' 'bare'
override CONFIG_OPT += **/rt/mode=rtbare
else
ifeq '$(rt/mode)' 'tiny'
override CONFIG_OPT += **/rt/mode=rttiny
else
ifeq '$(rt/mode)' 'pulpos'
override CONFIG_OPT += **/rt/mode=rt
else
$(error Unknown runtime mode: $(rt/mode))
endif
endif
endif
endif


help_opt_rt:
	@echo
	@echo "Available make options for runtime:"
	@echo "  rt/no-werror=1         Deactivate errors on warnings"
	@echo "  rt/mode=<mode>         Specify runtime mode (pulpos, tiny or bare)"
	