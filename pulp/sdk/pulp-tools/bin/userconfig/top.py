
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


def get_comp(config):
    if type(config) != dict and type(config) != OrderedDict:
        return None
    name = config.get('comp')
    if name is not None and name.find('chip') != -1:
        name = name.replace('chip_', '')
    if name is None:
        return Comp(config)
    else:
        return eval(name)(config)

class Comp(object):

    def __init__(self, config):

        self.comps = OrderedDict({})
        self.bindings = []

        for key, value in config.items():
            if key == 'bindings':
                self.bindings = value
            else:
                comp = get_comp(value)
                if comp is not None:
                    self.comps[key] = comp

        self.port_indexes = {}


    def gen(self):
        result = OrderedDict({})

        for key, value in self.comps.items():
            result[key] = value.gen()

        if len(self.bindings) != 0:
            result['bindings'] = []
            for binding in self.bindings:
                master, slave = binding
                result['bindings'] += self.get_bindings(master, slave)


        return result

    def get_comp_from_port(self, name):
        if 'self.' in name:
            return ['self', name.split('.')[1], self]
        else:
            return [name, name, self.comps.get(name)]


    def get_bindings(self, master, slave):

        bindings = []

        master_comp_name, master_port_name, master_comp = self.get_comp_from_port(master)
        slave_comp_name, slave_port_name, slave_comp = self.get_comp_from_port(slave)

        index = 0


        for port_name, port in master_comp.ports.items():
            if slave_port_name.find(port_name) == 0:
                if self.port_indexes.get(port_name) is None:
                    self.port_indexes[port_name] = 0
                port_index = self.port_indexes[port_name]
                self.port_indexes[port_name] = port_index + 1
                ports = port[port_index]

                for port in ports:

                    bindings.append(['%s.%s' % (master_comp_name, port), '%s.%s' % (slave_comp_name, slave_port_name)])
                    index += 1

                break




        #for port in master_comp.ports.get(slave_port_name):
        #    bindings.append(['%s.%s' % (master_comp_name, port), '%s.%s' % (slave_comp_name, slave_comp.ports.get(slave_port_name)[index])])
        #    index += 1

        if len(bindings) > 1:
            return [bindings]
        else:
            return bindings



class gap(Comp):

    ports = {
        'hyperram': [ ['hyper0'] ],
        'hyperflash': [ ['hyper0'] ],
        'spiflash': [ ['spim0'] ],
        'camera': [ ['cpi0', 'i2c0'] ],
        'microphone': [ ['i2s0' ], ['i2s1' ] ]
    }

    def gen(self):
        result = super(gap, self).gen()
        result['includes'] = ['gap.json']
        return result

class gap_name(Comp):

    def gen(self):
        result = super(gap_name, self).gen()
        result['gap'] = OrderedDict({})
        return result


class wolfe(Comp):

    ports = {
        'hyperram': [ ['hyper0'] ],
        'hyperflash': [ ['hyper0'] ],
        'spiflash': [ ['spim0'] ],
        'camera': [ ['cpi0', 'i2c0'] ],
        'microphone': [ ['i2s0' ], ['i2s1' ] ]
    }

    def gen(self):
        result = super(wolfe, self).gen()
        result['wolfe'] = OrderedDict({})
        result['wolfe']['includes'] = ['wolfe.json']
        return result


class vivosoc3(Comp):

    ports = {
        'hyperram': [ ['hyper0'] ],
        'hyperflash': [ ['hyper0'] ],
        'spiflash': [ ['spim0'] ],
    }

    def gen(self):
        result = super(vivosoc3, self).gen()
        result['vivosoc3'] = OrderedDict({})
        result['vivosoc3']['includes'] = ['vivosoc3.json']
        return result


class quentin(Comp):

    ports = {
        'hyperram': [ ['hyper0'] ],
        'hyperflash': [ ['hyper0'] ],
        'spiflash': [ ['spim0'] ],
        'camera': [ ['cpi0', 'i2c0'] ],
        'microphone': [ ['i2s0'], ['i2s1' ] ]
    }

    def gen(self):
        result = super(quentin, self).gen()
        result['quentin'] = OrderedDict({})
        result['quentin']['includes'] = ['quentin.json']
        return result



class pulpissimo(Comp):

    ports = {
        'spiflash': [ ['spim0'] ],
        'camera': [ ['cpi0', 'i2c0'] ],
        'microphone': [ ['i2s0'], ['i2s1' ] ]
    }

    def gen(self):
        result = super(pulpissimo, self).gen()
        result['pulpissimo'] = OrderedDict({})
        result['pulpissimo']['includes'] = ['pulpissimo.json']
        return result



class pulpino(Comp):

    ports = {
        'hyperram': [ ['hyper0'] ],
        'hyperflash': [ ['hyper0'] ],
        'spiflash': [ ['spim0'] ],
        'camera': [ ['cpi0', 'i2c0'] ],
        'microphone': [ ['i2s0_0' ] ]
    }

    def gen(self):
        result = super(pulpino, self).gen()
        result['pulpino'] = OrderedDict({})
        result['pulpino']['includes'] = ['pulpino.json']
        return result



class hyperram(Comp):

    ports = {
        'hyperram': [ ['in'] ]
    }

    def gen(self):
        result = super(hyperram, self).gen()
        result['includes'] = ['periphs/hyperflash.json']
        result['size'] = "0x00800000"
        return result



class hyperflash(Comp):

    ports = {
        'hyperflash': [ ['in'] ]
    }

    def gen(self):
        result = super(hyperflash, self).gen()
        result['includes'] = ['periphs/hyperflash.json']
        result['size'] = "0x00800000"
        return result



class spiflash(Comp):

    ports = {
        'spiflash': [ ['in'] ]
    }

    def gen(self):
        result = super(spiflash, self).gen()
        result['includes'] = ['periphs/spiflash.json']
        result['size'] = "0x00800000"
        return result



class microphone(Comp):

    ports = {
        'microphone': [ ['i2s'] ]
    }

    def gen(self):
        result = super(microphone, self).gen()
        result['includes'] = ['periphs/microphone.json']
        return result

class himax(Comp):

    ports = {
        'camera': [ ['in', 'i2c'] ]
    }

    def gen(self):
        result = super(himax, self).gen()
        result['includes'] = ['periphs/himax.json']
        return result

class ov7670(Comp):

    ports = {
        'camera': [ ['in', 'i2c'] ]
    }

    def gen(self):
        result = super(ov7670, self).gen()
        result['includes'] = ['periphs/ov7670.json']
        return result


class board(Comp):

    ports = {
        'camera': [ ['camera', 'camera_i2c'] ],
        'microphone': [ ['microphone' ] ]
    }


class Top(object):

    def __init__(self, name=None, config_path=None, config_string=None, config=None):
        self.name = name

        if config_path is not None:
            with open(config_path, 'r') as fd:
                config = json.load(fd, object_pairs_hook=OrderedDict)

        if config_string is not None:
            config = json.loads(config_string, object_pairs_hook=OrderedDict)

        self.comp = get_comp(config)

    def gen(self, path):
        config = self.comp.gen()

        with open(path, 'w') as file:
            json.dump(config, file, indent='  ')

    def gen_config(self):

        result = OrderedDict([
            ("includes", ["defaults.json", "pulp_system_common.json"])
        ])

        system = OrderedDict()

        system["system"] = self.name
        system.update(self.comp.gen())

        result["system_tree"] = system

        return result
