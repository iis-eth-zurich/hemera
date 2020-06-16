
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


import json
from collections import OrderedDict

try:
    import json_tools as js
except:
    pass

class Arg(object):

    def __init__(self, str):
        self.params = []
        self.name = str
        self.params_dict = {}
        if str.find('(') != -1:
            self.name = str.split('(', 1)[0]
            for arg_str in str.split('(', 1)[1][:-1].split(','):
                arg = Arg(arg_str)
                self.params.append(arg)
                self.params_dict[arg.name] = arg


    def get_params(self):
        return self.params

    def get_param(self, name):
        return self.params_dict.get(name)

    def get_param_value(self, name):
        param = self.params_dict.get(name)
        return param.params[0].name

    def get_name(self):
        return self.name

    def get_value(self):
        return self.name

    def dump(self, indent=0):
        print ('  '*indent + self.name)
        for arg in self.params:
            arg.dump(indent + 2)



def get_core_from_name(name):
  if name == 'riscyv2-fpu':
    return 'ri5ky_v2_fpu'
  elif name == 'riscyv2':
    return 'ri5ky_v2'
  elif name in ['zeroriscy', 'microriscy']:
    return name
  else:
    raise Exception('Unknown core: ' + name)


class Periph(object):

    def process(self, config, arg_list):
        return []

    def vp_bind(self, result, config):
        return []

    def preprocess_arg(self, config, arg, arg_list):
        return []



class Tool(object):

    def preprocess_arg(self, config, arg, arg_list):
        return []

    def handle_arg(self, config, arg, arg_list):
        pass


class Spim_verif(Periph):

    def bind(self, result, config):
        return [["pulp_chip->%s" % config.get('spi'), "spim_verif->spi"]]

    def handle_arg(self, config, arg, arg_list):
        config.set('periphs/spim_verif/spi', arg.get_params()[0].get_value())


class Uart_tb(Periph):

    def bind(self, result, config):
        return [
            ["pulp_chip->%s" % config.get('uart'), "uart_tb->uart"]
        ]

    def vp_bind(self, result, config):
        return [
            ["chip/padframe->%s_pad" % config.get('uart'), "dpi->%s" % config.get('uart')]
        ]

    def handle_arg(self, config, arg, arg_list):
        config.set('periphs/uart_tb/uart', arg.get_params()[0].get_value())



class Camera(Periph):

    def bind(self, result, config):
        return [
            ["pulp_chip->%s" % config.get('cpi'), "camera->cpi"]
        ]

    def handle_arg(self, config, arg, arg_list):
        config.set('periphs/camera/cpi', arg.get_params()[0].get_value())




class Jtag_proxy(Periph):

    def bind(self, result, config):
        return [
            ["pulp_chip->%s" % config.get('jtag'), "jtag_proxy->jtag"],
            ["pulp_chip->%s" % config.get('ctrl'), "jtag_proxy->ctrl"]
        ]

    def vp_bind(self, result, config):
        return [
            ["dpi->%s" % config.get('jtag'), "chip/padframe->%s_pad" % config.get('jtag')]
        ]

    def handle_arg(self, config, arg, arg_list):
        config.set('periphs/jtag_proxy/jtag', arg.get_params()[0].get_value())
        config.set('periphs/jtag_proxy/ctrl', arg.get_params()[1].get_value())




class Debug_bridge(Tool):

    def preprocess_arg(self, config, arg, arg_list):

        platform = arg_list.get('platform').get_param_value('name')
        if platform == 'gvsoc' or platform == 'rtl':
            return ['boot(jtag)', 'jtag_proxy(jtag0,ctrl)', 'debug-bridge']
        return []

    def handle_arg(self, config, arg, arg_list):
        pass

    def process(self, config, arg_list):
        if config.get('gdb') == 'jtag' or config.get('boot') is not None and config.get('boot').get() == 'jtag':
            return [
                ['system_tree/debug-bridge/cable/type', 'jtag-proxy'],
                ['system_tree/debug-bridge/boot-mode', 'jtag']
            ]
        return []



class Boot(Tool):

    def handle_arg(self, config, arg, arg_list):

        config.set('boot', arg.get_params()[0].get_value())

    def process(self, config, arg_list):
        return [['loader/boot/mode', 'jtag']]

class Gdb(Tool):


    def preprocess_arg(self, config, arg, arg_list):

        platform = arg_list.get('platform').get_param_value('name')
        if platform == 'gvsoc':
            return ['boot(jtag)', 'jtag_proxy(jtag0,ctrl)', 'debug-bridge']
        return []

    def process(self, config, arg_list):

        result = []

        platform = arg_list.get('platform').get_param_value('name')
        if platform == 'board':
            result.append(['system_tree/debug-bridge/commands', 'load ioloop reqloop start gdb wait'])

        result.append(['gdb/active', 'true'])

        return result






class Platform(Tool):

    def handle_arg(self, config, arg, arg_list):
        pass

    def process(self, config, arg_list):
        return []



peripherals = {
    'camera': Camera,
    'spim_verif': Spim_verif,
    'jtag_proxy': Jtag_proxy,
    'uart_tb': Uart_tb
}

tools = {
    'debug-bridge': Debug_bridge,
    'boot':         Boot,
    'gdb':          Gdb,
    'platform':     Platform
}


class Generic_template(object):

    def __init__(self, name=None, config={}):
        if name is not None:
            self.name = name
        self.config = config
        self.comps = {}
        self.props = {}

        for key, value in config.items():
            if key in 'template':
                continue

            if type(value) == OrderedDict or type(value) == dict:
                self.comps[key] = get_comp_from_config(key, value)
            else:
                self.props[key] = value

    def handle_periphs(self, result):
        periphs = self.config.get('periphs')

        if periphs is not None:
            if result.get('system_tree') is None:
                result['system_tree'] = OrderedDict()

            if result.get('system_tree').get('board') is None:
                result['system_tree']['board'] = OrderedDict()

            tb_comps = []
            bindings = []
            vp_bindings = []

            for name in periphs.keys():
                periph_config = periphs.get(name)

                instance_name = name
                index = 0
                while True:
                    if result['system_tree']['board'].get(instance_name) is None:
                        result['system_tree']['board'][instance_name] = OrderedDict([("includes", ['periph/%s.json' % name])])
                        tb_comps.append(instance_name)
                        break
                    instance_name = name + '_' + index
                    index += 1

                periph = peripherals.get(name)()

                bindings += periph.bind(result, periph_config)
                vp_bindings += periph.vp_bind(result, periph_config)

            result['system_tree']['board']['tb_comps'] = tb_comps
            result['system_tree']['board']['tb_bindings'] = bindings
            result['system_tree']['board']['vp_bindings'] = vp_bindings

    def gen(self, args=[]):
        for comp in self.comps.values():
            comp.gen(args)


class Pulpissimo(Generic_template):

    name = 'pulpissimo'

    def gen(self, args=[]):

        fc = self.config.get('fc')
        if fc is not None:
            core = fc.get('core')
            if core is not None:
                args.append(['**/fc/core', get_core_from_name(core)])

        result = OrderedDict()
        result['system'] = "pulpissimo"
        result["includes_eval"] = ["'pulpissimo_system.json'"]


        install_name = self.config.get('install_name')
        if install_name is not None:
            result['install_name'] = install_name

        return result



class Quentin(Generic_template):

    name = 'quentin'

    def gen(self, args=[]):

        result = OrderedDict()
        result['system'] = "quentin"
        result["includes_eval"] = ["'quentin_system.json'"]


        install_name = self.config.get('install_name')
        if install_name is not None:
            result['install_name'] = install_name

        return result


class Fulmine(Generic_template):

    name = 'fulmine'

    def gen(self, args=[]):

        result = OrderedDict()
        result['system'] = "fulmine"
        result["includes_eval"] = ["'fulmine_system.json'"]


        install_name = self.config.get('install_name')
        if install_name is not None:
            result['install_name'] = install_name

        return result


class Vivosoc2(Generic_template):

    name = 'vivosoc2'

    def gen(self, args=[]):

        result = OrderedDict()
        result['system'] = "vivosoc2"
        result["includes_eval"] = ["'vivosoc2_system.json'"]


        install_name = self.config.get('install_name')
        if install_name is not None:
            result['install_name'] = install_name

        return result


class Vivosoc2_1(Generic_template):

    name = 'vivosoc2_1'

    def gen(self, args=[]):

        result = OrderedDict()
        result['system'] = "vivosoc2_1"
        result["includes_eval"] = ["'vivosoc2_1_system.json'"]


        install_name = self.config.get('install_name')
        if install_name is not None:
            result['install_name'] = install_name

        return result


class Gap(Generic_template):

    name = 'gap'

    def gen(self, args=[]):

        result = OrderedDict()
        result['system'] = "gap"
        result["includes_eval"] = ["'gap_system.json'"]


        install_name = self.config.get('install_name')
        if install_name is not None:
            result['install_name'] = install_name

        return result


class neuraghe(Generic_template):

    name = 'neuraghe'

    def gen(self, args=[]):

        result = OrderedDict()
        result['system'] = "neuraghe"
        result["includes_eval"] = ["'neuraghe_system.json'"]


        install_name = self.config.get('install_name')
        if install_name is not None:
            result['install_name'] = install_name

        return result


class Vega(Generic_template):

    name = 'vega'

    def gen(self, args=[]):

        result = OrderedDict()
        result['system'] = "vega"
        result["includes_eval"] = ["'vega_system.json'"]


        install_name = self.config.get('install_name')
        if install_name is not None:
            result['install_name'] = install_name

        return result



class Bigpulp(Generic_template):

    name = 'bigpulp'

    def gen(self, args=[]):

        result = OrderedDict()
        result['system'] = "bigpulp"
        result["includes_eval"] = ["'bigpulp_system.json'"]


        install_name = self.config.get('install_name')
        if install_name is not None:
            result['install_name'] = install_name

        return result



class Hero_z_7045(Generic_template):

    name = 'hero-z-7045'

    def gen(self, args=[]):

        result = OrderedDict()
        result['system'] = "hero-z-7045"
        result["includes_eval"] = ["'hero-z-7045_system.json'"]


        install_name = self.config.get('install_name')
        if install_name is not None:
            result['install_name'] = install_name

        return result




class Honey(Generic_template):

    name = 'honey'

    def gen(self, args=[]):

        result = OrderedDict()
        result['system'] = "honey"
        result["includes_eval"] = ["'honey_system.json'"]


        install_name = self.config.get('install_name')
        if install_name is not None:
            result['install_name'] = install_name

        return result



class Vivosoc3(Generic_template):

    name = 'vivosoc3'

    def gen(self, args=[]):

        result = OrderedDict()
        result['system'] = "vivosoc3"
        result["includes_eval"] = ["'vivosoc3_system.json'"]


        install_name = self.config.get('install_name')
        if install_name is not None:
            result['install_name'] = install_name

        return result



class Multino(Generic_template):

    name = 'multino'

    def gen(self, args=[]):

        result = OrderedDict()
        result['system'] = "multino"
        result["includes_eval"] = ["'multino_system.json'"]


        install_name = self.config.get('install_name')
        if install_name is not None:
            result['install_name'] = install_name

        return result



class Wolfe(Generic_template):

    name = 'wolfe'

    def gen(self, args=[]):

        result = OrderedDict()
        result['system'] = "wolfe"
        result["includes_eval"] = ["'wolfe_system.json'"]


        install_name = self.config.get('install_name')
        if install_name is not None:
            result['install_name'] = install_name

        return result



class Oprecompkw(Generic_template):

    name = 'oprecompkw'

    def gen(self, args=[]):

        result = OrderedDict()
        result['system'] = "oprecompkw"
        result["includes_eval"] = ["'oprecompkw_system.json'"]


        install_name = self.config.get('install_name')
        if install_name is not None:
            result['install_name'] = install_name

        return result



class Pulp(Generic_template):

    name = 'pulp'

    def gen(self, args=[]):

        result = OrderedDict()
        result['system'] = "pulp"
        result["includes_eval"] = ["'pulp_system.json'"]


        install_name = self.config.get('install_name')
        if install_name is not None:
            result['install_name'] = install_name

        return result


class Top_template(Generic_template):

    name = 'top'

    def gen(self, args=[]):


        result = OrderedDict([
            ("includes", ["defaults.json"])
        ])

        system = OrderedDict()

        result.update(self.comps.get('chip').gen(args))

        self.handle_periphs(result)

        return result

templates = [ Pulpissimo, Quentin, Pulp, Gap, neuraghe, Vega, Fulmine, Vivosoc2, Vivosoc2_1, Bigpulp, Hero_z_7045, Oprecompkw, Wolfe, Multino, Vivosoc3, Honey ]


def get_comp_from_config(name, config):

    template_name = config.get('template')

    if template_name is None:
        return Generic_template(name, config)

    for template in templates:
        if template_name == template.name:
            return template(name, config)

    raise Exception('Unknown template: ' + template_name)



class Top(object):

    def __init__(self, name=None, config_path=None, config_string=None, config=None, props=None, args=None):
        self.name = name
        self.config_args = []

        if config_path is not None:
            with open(config_path, 'r') as fd:
                config = json.load(fd, object_pairs_hook=OrderedDict)

        if config_string is not None:
            config = json.loads(config_string, object_pairs_hook=OrderedDict)

        args_objects = []
        arg_list = {}

        try:
            js_config = js.import_config(config)

            if args is not None:

                for name2 in args.split(':'):
                    for name in name2.split(' '):
                        arg = Arg(name)
                        arg_list[arg.name] = arg


                extra_args = []
                for arg in arg_list.values():
                    extra_args += self.preprocess_arg(js_config, arg, arg_list)


                for extra_arg in extra_args:
                    arg = Arg(extra_arg)
                    arg_list[arg.name] = arg

                for arg in arg_list.values():
                    args_objects += self.handle_arg(js_config, arg, arg_list)

            if props is not None:
                for arg in props.split(':'):
                    key, value = arg.split('=')
                    js_config.set(key, value)

            config = js_config.get_dict()

        except:
            pass

        if args_objects is not None:
            for arg_object in args_objects:
                self.config_args += arg_object.process(js_config, arg_list)

        self.top = Top_template(config=config)

    def preprocess_arg(self, config, arg, arg_list):

        result = []

        periph = peripherals.get(arg.get_name())
        if periph is not None:
            result += periph().preprocess_arg(config=config, arg=arg, arg_list=arg_list)

        tool = tools.get(arg.get_name())
        if tool is not None:
            result += tool().preprocess_arg(config=config, arg=arg, arg_list=arg_list)

        return result

    def handle_arg(self, config, arg, arg_list):

        result = []

        periph = peripherals.get(arg.get_name())
        if periph is not None:
            obj = periph()
            result.append(obj)
            obj.handle_arg(config=config, arg=arg, arg_list=arg_list)

        tool = tools.get(arg.get_name())
        if tool is not None:
            obj = tool()
            result.append(obj)
            obj.handle_arg(config=config, arg=arg, arg_list=arg_list)

        return result


    def gen_config(self):
        return self.top.gen(self.config_args), self.config_args

    def gen(self, path):

        config = self.top.gen(self.config_args)

        with open(path, 'w') as file:
            json.dump(config, file, indent='  ')
