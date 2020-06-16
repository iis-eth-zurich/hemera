
#
# Copyright (C) 2018 ETH Zurich and University of Bologna
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

header_pattern="""
OUTPUT_ARCH({pulp_core_family})
ENTRY( _start )
"""


class Memory(object):

    def __init__(self, name, origin, length, alias_origin=None,
                 alias_length=None):
        self.name = name
        self.alias_name = name + '_aliased'
        self.origin = origin
        self.length = length
        self.alias_origin = alias_origin
        self.alias_length = alias_length
        self.sections = []

    def gen(self, file):

        file.write('  %-18s : ORIGIN = 0x%8.8x, LENGTH = 0x%8.8x\n' %
                   (self.name, self.origin, self.length))
        if self.alias_origin is not None:
            file.write('  %-18s : ORIGIN = 0x%8.8x, LENGTH = 0x%8.8x\n' %
                       (self.alias_name, self.alias_origin, self.alias_length))

    def get_name(self, use_alias=False):
        if use_alias:
            return self.alias_name
        else:
            return self.name

    def add_section(self, section):
        if len(self.sections) != 0:
            self.sections[-1].is_last = False
            section.set_prev_section(self.sections[-1])
        self.sections.append(section)
        section.is_last = True


class Variable(object):

    def __init__(self, script, value):
        self.value = value
        script.add_variable(self)

    def gen(self, file):
        file.write('%s\n' % self.value)


class SectionVariable(object):

    def __init__(self, script, value):
        self.value = value
        script.add_section(self)

    def gen(self, file):
        file.write('  %s\n\n' % self.value)


class Section(object):

    def __init__(self, script, name, memory, align=4, use_alias=False,
                 load_address=None, exec_address=None, shadow=None,
                 nb_instances=None, start_symbol=None, end_symbol=None,
                 load_address_direct=False):
        self.name = name
        self.memory = memory
        self.align = align
        self.prev = None
        self.load_address = load_address
        self.exec_address = exec_address
        self.shadow = shadow
        self.nb_instances = nb_instances
        script.add_section(self)
        self.lines = []
        self.use_alias = use_alias
        self.start_symbol = start_symbol
        self.end_symbol = end_symbol
        self.load_address_direct = load_address_direct
        memory.add_section(self)

    def add(self, lines):
        self.lines += lines

    def set_prev_section(self, prev):
        self.prev = prev

    def get_exec_address(self, resolve, use_alias=False):
        if self.exec_address is not None:
            return self.exec_address
        else:
            if resolve:
                if use_alias != self.use_alias or self.shadow is not None:
                    return 'ORIGIN(%s)' % \
                        (self.memory.get_name(use_alias=use_alias))
                else:
                    return 'ADDR(.%s)' % (self.get_name())
            else:
                return None

    def use_exec_address(self):
        if self.shadow is not None or self.prev is not None and self.prev.use_exec_address():
            return True
        if self.use_alias:
            return True
        return False

    def get_size(self):
        if self.nb_instances is None:
            return 'SIZEOF(.%s)' % self.get_shadow_name()
        else:
            return 'SIZEOF(.%s) * %s' % (self.get_shadow_name(), self.nb_instances)

    def get_address_hierarchy(self, use_alias, is_self=True):
        address = self.get_exec_address(use_alias=use_alias, resolve=False)
        if address is None:
            if not is_self and self.use_alias == use_alias \
                    and self.shadow is None or self.prev is None:
                if is_self:
                    address = ''
                else:
                    address = self.get_exec_address(use_alias=use_alias,
                                                    resolve=True)
            else:
                address = self.prev.get_address_hierarchy(
                    use_alias=use_alias, is_self=False)

        if not is_self:
            return address + ' + %s' % self.get_size()
        else:
            return address

    def get_exec_address_hierarchy(self):
        if self.use_exec_address():
            address = self.get_address_hierarchy(self.use_alias)
        else:
            address = ''
        if address == '':
            return ''
        else:
            return '(' + address + ')'

    def get_load_address(self, use_alias=False, is_self=True, resolve=False, direct=False):
        if self.load_address is not None and not direct:
            return self.load_address
        else:
            if self.use_alias:
                return 'ORIGIN(%s)' % (self.memory.get_name())
            elif is_self and not resolve:
                return ''
            else:
                return 'ADDR(.%s)' % (self.get_name())

    def has_load_address(self):
        #if self.shadow is not None:
        #    return True
        if self.use_alias:
            return True

        if self.prev is not None:
            return self.prev.has_load_address()
        else:
            return self.load_address is not None or self.use_alias

    def get_load_address_hierarchy(self, use_alias=None, is_self=True, resolve=False, direct=False):

        #resolve = resolve or self.shadow is not None

        direct = direct or self.load_address_direct

        if self.has_load_address() or resolve:

            if self.has_load_address():
                resolve = True

            if use_alias is not None:
                use_alias = self.use_alias

            if self.prev is None:
                address = self.get_load_address(
                    is_self=is_self, use_alias=use_alias, resolve=resolve, direct=direct)
            else:
                address = self.prev.get_load_address_hierarchy(
                    is_self=False, use_alias=use_alias, resolve=resolve, direct=direct)
        else:
            address = ''

        if is_self:
            if address != '':
                return ' AT(' + address + ')'
            else:
                return ''
        else:
            return address + ' + %s' % self.get_size()

    def get_name(self):

        section_name = self.name
        if self.shadow is not None:
            section_name += '_s'

        return section_name

    def get_shadow_name(self):
        return self.name

    def gen(self, file):

        file.write(
            '  .%s %s:%s\n' %
            (self.get_name(), self.get_exec_address_hierarchy(),
             self.get_load_address_hierarchy()))
        file.write('  {\n')

        if self.align is not None and (len(self.lines) != 0 or self.start_symbol is not None or self.end_symbol is not None or self.is_last):
            file.write('    . = ALIGN(%d);\n' % (self.align))

        if self.start_symbol is not None:
            file.write('    %s = .;\n' % (self.start_symbol))

        if self.shadow is None:
            for line in self.lines:
                file.write('    %s\n' % line)
            if self.end_symbol is not None:
                file.write('    %s = .;\n' % (self.end_symbol))
            if self.is_last:
                file.write('    __%s_end = ABSOLUTE(.);\n' % (self.memory.get_name(self.use_alias)))
        file.write('  } > %s\n' % self.memory.get_name(self.use_alias))
        file.write('\n')




class Link_script(object):

  def __init__(self, config):
    self.config = config
    self.args = {}
    self.memories = []
    self.sections = []
    self.variables = []


    if config.get('host') is not None:
      self.__gen_host(config)
    else:
      self.__gen_fabric(config)



  def __gen_host(self, config):
    self.args['pulp_core_family'] = self.config.get('host/archi')

    ddr = Memory('ddr', self.config.get_int('soc/host_ico/ddr/base'),
                 self.config.get_int('ddr/size'))
    l2 = Memory('l2', self.config.get_int('soc/host_ico/l2/base'),
                 self.config.get_int('l2/size'))
    self.memories.append(ddr)
    self.memories.append(l2)

    text     = Section(self, 'text',              l2)
    data     = Section(self, 'data',              l2)
    bss      = Section(self, 'bss',               l2)
    SectionVariable(self, '_fbss = ALIGN(8);')
    stack    = Section(self, 'stack',             l2)
    SectionVariable(self, '_end = ALIGN(8);')


    text.add([    
      '*(.text)',
      '*(.text.*)', 
      '*(.boot)',
      '*(.boot.*)',
    ])

    data.add([
      '*(.data);',
      '*(.data.*)',
      '*(.sdata);',
      '*(.sdata.*)',
    ])    
    
    bss.add([
      '_bss_start = .;',
      '*(.bss)',
      '*(.bss.*)',
      '*(.sbss)',
      '*(.sbss.*)',
      '*(COMMON)',
      '. = ALIGN(4);',
      '_bss_end = .;',
    ])

    stack.add([
      '. = ALIGN(16);',
      '. = . + 0x%x;' % (self.config.get_int('stack_size')),
      'stack = .;'
    ])


  def __gen_fabric(self, config):
    has_fc = self.config.get('fc/archi') is not None
    if has_fc:
      core_family = self.config.get('fc/archi')
    else:
      core_family = self.config.get('pe/archi')
    
    self.args['pulp_core_family'] = core_family
    l1 = None
    l2_fc_code = None
    l2_fc_data = None
    l2 = None

    l2_alias = self.config.get('l2_alias')



    if config.get('l2') is not None:
      if not config.get_int('l2/is_partitioned'):
        l2Size = config.get_int('l2/size')
        l2Base = config.get_int('l2/map_base')
        if l2_alias:
          l2 = Memory('L2', l2Base, l2Size, 0x4, l2Size - 4)
        else:
          l2 = Memory('L2', l2Base, l2Size)
        l2_fc_code = l2
        l2_data = l2
        l2_fc_data = l2
        l2_fc_shared_data = l2
        self.memories.append(l2)

    l2_priv0_size = config.get_int('l2_priv0/size')
    if l2_priv0_size != None:
      l2_priv0_base = config.get_int('l2_priv0/map_base')
      l2_fc_data = Memory('L2_priv0', l2_priv0_base + 4, l2_priv0_size - 4, 0x4, l2_priv0_size - 4)
      l2_data = l2_fc_data
      self.memories.append(l2_fc_data)

    l2_priv1_size = config.get_int('l2_priv1/size')
    if l2_priv1_size != None:
      l2_priv1_base = config.get_int('l2_priv1/map_base')
      l2_fc_code = Memory('L2_priv1', l2_priv1_base, l2_priv1_size)
      self.memories.append(l2_fc_code)

    l2_shared_size = config.get_int('l2_shared/size')
    if l2_shared_size != None and config.get_int('l2/is_partitioned'):
      l2_shared_base = config.get_int('l2_shared/map_base')
      l2 = Memory('L2_shared', l2_shared_base, l2_shared_size)
      l2_fc_shared_data = l2
      self.memories.append(l2)

    l1Size = config.get_int('l1/size')
    if l1Size != None:
      l1Base = config.get_int('l1/map_base')
      l1_alias_base = config.get_int('l1/alias_base')

      if l1_alias_base is None:
        l1_alias_base = 0x0



      l1 = Memory('L1', l1Base+0x4, l1Size, l1_alias_base + 0x4, l1Size - 4)
      self.memories.append(l1)

    if not has_fc:
        l2_fc_data = l1
        l2_fc_shared_data = l1



    Variable(self, '__ZERO  = 0;')
    Variable(self, '__USE_UART = 0;')
    Variable(self, '__RT_DEBUG_CONFIG   = (0 << 8) | 0;')
    Variable(self, '__FC   = 1;')
    Variable(self, '__L2   = 0x80000;')
    Variable(self, '__L1Cl = 0x10000;')
    Variable(self, '__FETCH_ALL = 0x0;')
    Variable(self, '__ACTIVE_FC = 0x1;')
    Variable(self, '__rt_stack_size = 0x%x;' % (self.config.get_int('stack_size')))
    if config.get('cluster/nb_pe') != None:
      Variable(self, '__NB_ACTIVE_PE = %d;' % (config.get_int('cluster/nb_pe')))

    platform = 0
    if config.get('platform') == 'fpga':
      platform = 1
    elif config.get('platform') == 'rtl':
      platform = 2
    elif config.get('platform') == 'gvsoc':
      platform = 3
    elif config.get('platform') == 'board':
      platform = 4
    Variable(self, '__rt_platform = %d;' % platform)

    iodev = config.get('rt/iodev')

    iodevs_conf = config.get_config('rt/iodevs')

    Variable(self, '__rt_iodev = %s;' % (iodevs_conf.get_config(iodev).value()))

    for iodev_name in iodevs_conf.keys():
        iodev_conf = iodevs_conf.get_config(iodev_name)
        for item_name in iodev_conf.keys():
            Variable(self, '%s = %s;' % ('__rt_iodev_%s_%s' % (iodev_name, item_name), iodev_conf.get(item_name)))



    if config.get('nb_cluster') != None and config.get('nb_cluster') != 0:
      Variable(self, '__rt_nb_cluster = %s;' % (config.get('nb_cluster')))
      Variable(self, '__rt_nb_pe = %s;' % (config.get('cluster/nb_pe')))
    if self.config.get('rt/cl_master_stack_size') is not None:
        Variable(self, '__rt_cl_master_stack_size = 0x%x;' % self.config.get('rt/cl_master_stack_size'))
    if self.config.get('rt/cl_slave_stack_size') is not None:
        Variable(self, '__rt_cl_slave_stack_size = 0x%x;' % self.config.get('rt/cl_slave_stack_size'))

    config_trace_value = 0
    warning = 0
    werror = 0
    if self.config.get('rt/trace'):
      traces = self.config.get('rt/traces')
      if traces == None or traces == 'all': config_trace_value = 0xffffffff
      else:
        for trace in traces.split(','):
          if trace == 'init': config_trace_value |= (1<<0)
          elif trace == 'alloc': config_trace_value |= (1<<1)

    if self.config.get('rt/warnings') is not None: warning = self.config.get_bool('rt/warnings')
    if self.config.get('rt/werror') is not None: werror = self.config.get_bool('rt/werror')

    config_value = (warning << 0) | (werror << 1)

    rt_config_value = 0

    if self.config.get('soc/cluster') is not None and self.config.get('rt/start-all'):

        if self.config.get('rt/fc-start') == False or self.config.get('rt/cluster-start'):
            rt_config_value |= 1<<0
        if self.config.get('rt/fc-start'):
            rt_config_value |= 1<<1

    Variable(self, '__rt_config = 0x%x;' % rt_config_value)
    Variable(self, '__rt_debug_init_config = 0x%x;' % config_value)
    Variable(self, '__rt_debug_init_config_trace = 0x%x;' % config_trace_value)

    if core_family == 'or1k':
        if self.config.get_bool('rt/libc'):
          Variable(self, 'GROUP( -lc -lgcc )')
        else:
          Variable(self, 'GROUP( -lgcc )')
    else:  
        if self.config.get_bool('rt/libc'):
          Variable(self, 'GROUP( -lc -lgloss -lgcc )')
        else:
          Variable(self, 'GROUP( -lgloss -lgcc )')

    vectors = Section(self, 'vectors', l2_fc_code)
    l1FcTiny = Section(self, 'l1FcTiny', l2_fc_data, use_alias=l2_alias)
    data_tiny_fc = Section(self, 'data_tiny_fc', l2_fc_data, use_alias=l2_alias)
    text     = Section(self, 'text',              l2_fc_code)
    SectionVariable(self, '__fc_code_end = ALIGN(8);')
    init     = Section(self, 'init',              l2_fc_data)
    fini     = Section(self, 'fini',              l2_fc_data)
    preinit_array = Section(self, 'preinit_array',              l2_fc_data)
    init_array    = Section(self, 'init_array',              l2_fc_data)
    fini_array    = Section(self, 'fini_array',              l2_fc_data)
    boot     = Section(self, 'boot',              l2_fc_data)
    rodata   = Section(self, 'rodata',            l2_data)
    got      = Section(self, 'got',               l2_fc_data)
    shbss    = Section(self, 'shbss',             l2_fc_data)
    talias   = Section(self, 'talias',            l2_fc_data)
    offload_funcs = Section(self, 'gnu.offload_funcs', l2_fc_data)
    offload_vars  = Section(self, 'gnu.offload_vars',  l2_fc_data)
    stack    = Section(self, 'stack',             l2_fc_data)
    data_fc  = Section(self, 'data_fc',  l2_fc_data)
    data_fc_shared  = Section(self, 'data_fc_shared',  l2_fc_shared_data)

    if l1 != None:

      l1_use_alias = self.config.get_bool('cluster/has_l1_alias')

      if has_fc:
        data_tiny_l1 = Section(self, 'data_tiny_l1', l1, use_alias=l1_use_alias, load_address='_l1_preload_start_inL2', start_symbol='_l1_preload_start')
        tls           = Section(self, 'tls',           l1, use_alias=l1_use_alias, nb_instances='__NB_ACTIVE_PE')
        heapsram      = Section(self, 'heapsram',      l1, use_alias=l1_use_alias)
        l1cluster_g   = Section(self, 'l1cluster_g',   l1, use_alias=False)

        SectionVariable(self, '__l1_heap_start = ALIGN(4);')
        SectionVariable(self, '__l1_heap_size = LENGTH(L1) - __l1_heap_start + ORIGIN(L1);')
        SectionVariable(self, '_heapsram_size = LENGTH(L1) - _heapsram_start + ORIGIN(L1);')
        SectionVariable(self, '_l1_preload_size = SIZEOF(.data_tiny_l1) + SIZEOF(.tls) + SIZEOF(.heapsram) + SIZEOF(.l1cluster_g);')

        bss_l1   = Section(self, 'bss_l1',   l1, use_alias=False, load_address_direct=True)

        data_tiny_l1_l2s = Section(self, 'data_tiny_l1',   l2_data, shadow=data_tiny_l1, start_symbol='_l1_preload_start_inL2')
        tls_l2s           = Section(self, 'tls',           l2_data, shadow=tls, nb_instances='__NB_ACTIVE_PE')
        heapsram_l2s      = Section(self, 'heapsram',      l2_data, shadow=heapsram)
        l1cluster_g_l2s   = Section(self, 'l1cluster_g',   l2_data, shadow=l1cluster_g)

      else:
        data_tiny_l1 = Section(self, 'data_tiny_l1', l1, use_alias=l1_use_alias)
        tls           = Section(self, 'tls',           l1, use_alias=l1_use_alias, nb_instances='__NB_ACTIVE_PE')
        heapsram      = Section(self, 'heapsram',      l1, use_alias=l1_use_alias)
        l1cluster_g   = Section(self, 'l1cluster_g',   l1, use_alias=False)

        SectionVariable(self, '__l1_heap_start = ALIGN(4);')
        SectionVariable(self, '__l1_heap_size = LENGTH(L1) - __l1_heap_start + ORIGIN(L1);')
        SectionVariable(self, '_heapsram_size = LENGTH(L1) - _heapsram_start + ORIGIN(L1);')
        SectionVariable(self, '_l1_preload_size = SIZEOF(.data_tiny_l1) + SIZEOF(.tls) + SIZEOF(.heapsram) + SIZEOF(.l1cluster_g);')

        bss_l1   = Section(self, 'bss_l1',   l1, use_alias=False)

    data     = Section(self, 'data',              l2_data)
    heapl2ram         = Section(self, 'heapl2ram', l2_data)
    bss      = Section(self, 'bss',               l2_data, start_symbol='_bss_start', end_symbol='_bss_end', align=8)


    for section_desc in self.config.get('user-sections'):
        section_name, mem_name = section_desc.split('@')

        found_memory = None
        for memory in self.memories:
            if memory.name == mem_name:
                found_memory = memory

        if found_memory is None:
            names = []
            for memory in self.memories:
                names.append(memory.name)

            raise Exception("Didn't find memory %s for user section %s, available memories: %s" % (mem_name, section_name, ", ".join(names)))

        section   = Section(self, section_name, found_memory, start_symbol='__%s_start' % (section_name), end_symbol='__%s_end' % (section_name))
        section.add([
          '*(.%s)' % (section_name),
          '*(.%s.*)' % (section_name),
        ])
        SectionVariable(self, '__%s_size = __%s_end - __%s_start;' % (section_name, section_name, section_name))



    if config.get_int('fc_tcdm/size') is None:
      SectionVariable(self, '__fc_data_end = ALIGN(8);')


    shared      = Section(self, 'shared',         l2)
    SectionVariable(self, '__l2_data_end = ALIGN(8);')

    SectionVariable(self, '__cluster_text_size = __cluster_text_end - __cluster_text_start;')

    if config.get_int('l2_priv0/size') == None:
      SectionVariable(self, '__l2_heap_start = ALIGN(4);')
      SectionVariable(self, '__l2_heap_size = LENGTH(L2) - __l2_heap_start + ORIGIN(L2);')
    else:
      SectionVariable(self, '__l2_priv0_heap_start = __fc_data_end;')
      SectionVariable(self, '__l2_priv0_heap_size = LENGTH(L2_priv0) - __l2_priv0_heap_start + ORIGIN(L2_priv0);')

      SectionVariable(self, '__l2_priv1_heap_start = __fc_code_end;')
      SectionVariable(self, '__l2_priv1_heap_size = LENGTH(L2_priv1) - __l2_priv1_heap_start + ORIGIN(L2_priv1);')

      SectionVariable(self, '__l2_shared_heap_start = __l2_data_end;')
      SectionVariable(self, '__l2_shared_heap_size = LENGTH(L2_shared) - __l2_shared_heap_start + ORIGIN(L2_shared);')

    if config.get_int('fc_tcdm/size') is not None:
      SectionVariable(self, '__fc_tcdm_heap_start = __fc_tcdm_end;')
      SectionVariable(self, '__fc_tcdm_heap_size = LENGTH(fc_tcdm) - __fc_tcdm_heap_start + ORIGIN(fc_tcdm);')




    vectors.add([
      '__irq_vector_base = .;'
      'KEEP(*(.vectors))'
    ])

    l1FcTiny.add([
      '_l1FcShared_start = .;',
      '*(.l1FcTiny)',
      '*(.l1FcTiny.*)',
      '*(.fcTcdmTiny)',
      '*(.fcTcdmTiny.*)',
      '. = ALIGN(4);',
      '_l1FcShared_end = .;'
    ])

    data_tiny_fc.add([
      '*(.data_tiny_fc)',
      '*(.data_tiny_fc.*)',
    ])

    data_fc.add([
      '*(.data_fc)',
      '*(.data_fc.*)',
    ])

    data_fc_shared.add([
      '*(.data_fc_shared)',
      '*(.data_fc_shared.*)',
    ])
    
    text.add([    
      '_stext = .;',
      '*(.text)',
      '*(.text.*)',
      '. = ALIGN(4);',
      '__cluster_text_start = .;'
      "*(.cluster.text)",
      "*(.cluster.text.*)",
      '__cluster_text_end = .;'
      '_etext  =  .;',
      '*(.lit)',
      '*(.shdata)',
      '_endtext = .;'
    ])

    init.add([
      'KEEP( *(.init) )'
    ])

    fini.add([
      'KEEP( *(.fini) )'
    ])

    preinit_array.add([
      'PROVIDE_HIDDEN (__preinit_array_start = .);',
      'KEEP (*(.preinit_array))',
      'PROVIDE_HIDDEN (__preinit_array_end = .);',
    ])

    init_array.add([
      'PROVIDE_HIDDEN (__init_array_start = .);',
      '__CTOR_LIST__ = .;',
      'LONG((__CTOR_END__ - __CTOR_LIST__) / 4 - 2)',
      'KEEP(*(.ctors.start))',
      'KEEP(*(.ctors))',
      'KEEP (*(SORT(.init_array.*)))',
      'KEEP (*(.init_array ))',
      'LONG(0)',
      '__CTOR_END__ = .;',
      'PROVIDE_HIDDEN (__init_array_end = .);',
    ])

    fini_array.add([
      'PROVIDE_HIDDEN (__fini_array_start = .);',
      '__DTOR_LIST__ = .;',
      'LONG((__DTOR_END__ - __DTOR_LIST__) / 4 - 2)',
      'KEEP(*(.dtors.start))',
      'KEEP(*(.dtors))',
      'LONG(0)',
      '__DTOR_END__ = .;',
      'KEEP (*(SORT(.fini_array.*)))',
      'KEEP (*(.fini_array ))',
      'PROVIDE_HIDDEN (__fini_array_end = .);',
    ])

    boot.add([    
      '*(.boot)',
      '*(.boot.data)',
    ])

    rodata.add([
      '*(.rodata);',
      '*(.rodata.*)',
      '*(.srodata);',
      '*(.srodata.*)',
      '*(.eh_frame*)',
    ])

    got.add([
      '*(.got.plt) * (.igot.plt) *(.got) *(.igot)'
    ])

    shbss.add([
      '*(.shbss)'
    ])

    offload_funcs.add([
      'KEEP(*(.gnu.offload_funcs))'
    ])

    offload_vars.add([
      'KEEP(*(.gnu.offload_vars))'
    ])
     
    data.add([
      'sdata  =  .;',
      '_sdata  =  .;',
      '*(.data);',
      '*(.data.*)',
      '*(.sdata);',
      '*(.sdata.*)',
      '. = ALIGN(4);',
      'edata  =  .;',
      '_edata  =  .;',
    ])    
    
    bss.add([
      '*(.bss)',
      '*(.bss.*)',
      '*(.sbss)',
      '*(.sbss.*)',
      '*(COMMON)',
      '. = ALIGN(4);',
    ])

    shared.add([
      '*(.l2_data)',
      '*(.l2_data.*)',
    ])

    stack.add([
      '. = ALIGN(16);',
      '. = . + 0x%x;' % (self.config.get_int('stack_size')),
      'stack = .;'
    ])

    if l1 != None:

      data_tiny_l1.add([
        '*(.data_tiny_l1)',
        '*(.data_tiny_l1.*)',
        '*(.data_alias_l1)',
        '*(.data_alias_l1.*)',
      ])
      
      tls.add([
        '_tls_start = .;',
        '*(.tls)',
        '*(.tls.*)',
        '. = ALIGN(4);',
        '_tls_end = .;',
      ])

      heapsram.add([
        '*(.heapsram)',
        '*(.heapsram.*)',
      ]) 

      l1cluster_g.add([
        '*(.l1cluster_g)',
        '*(.l1cluster_g.*)',
        '*(.data_l1)',
        '*(.data_l1.*)',
        '. = ALIGN(4);',
        '_libgomp_start = .;',
        '*(.libgomp)',
        '*(.libgomp.*)',
        '. = ALIGN(4);',
        '_heapsram_start = .;',
      ])

      bss_l1.add([
        '*(.bss_l1)',
        '*(.bss_l1.*)',
        '_heapsram_start = .;',
      ])

    heapl2ram.add([
      '*(.heapl2ram)',
      '*(.fcTcdm)',
      '*(.fcTcdm.*)',
      '*(.fcTcdm_g)',
      '*(.fcTcdm_g.*)',
    ])


  def add_section(self, section):
    self.sections.append(section)

  def add_variable(self, section):
    self.variables.append(section)

  def gen(self, file, prop_file):
    if file is not None:
      file.write(header_pattern.format(**self.args))

      file.write('MEMORY\n')
      file.write('{\n')
      for mem in self.memories:
        mem.gen(file)
      file.write('}\n')
      file.write('\n')

      file.write('SECTIONS\n')
      file.write('{\n')
      for section in self.sections:
        section.gen(file)
      file.write('}\n')

    if prop_file is not None:
      for var in self.variables:
        var.gen(prop_file)
      prop_file.write('\n')



def gen_link_script(file, prop_file, config):
  link = Link_script(config)
  link.gen(file, prop_file)
