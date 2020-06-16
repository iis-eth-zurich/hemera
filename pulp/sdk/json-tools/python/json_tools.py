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

# 
# Authors: Germain Haugou, ETH (germain.haugou@iis.ee.ethz.ch)
#

import json
from collections import OrderedDict
import os

def get_paths(path=None, paths=None):
  all_paths = os.environ['PULP_CONFIGS_PATH'].split(':')
  if paths is not None:
    all_paths = all_paths + paths
  if path is not None:
    all_paths = all_paths + [path]
  return all_paths



def find_config(config, paths):

  for path in paths:
    full_path = os.path.join(path, config)
    if os.path.exists(full_path):
      return full_path

  return None



def import_config(config, interpret=False, path=None):
    return config_object(config, interpret, path)



def import_config_from_file(file_path, interpret=False, find=False, path=None):
    if find:
        paths = get_paths(path=path)
        new_file_path = find_config(file_path, paths)
        if new_file_path is None:
            raise Exception("Didn't find JSON file from any specified path (file: %s, paths: %s)" % (file_path, ":".join(paths)))
        file_path = new_file_path

    with open(file_path, 'r') as fd:
        config_dict = json.load(fd, object_pairs_hook=OrderedDict)
        return import_config(config_dict, interpret, path=os.path.dirname(file_path))


class config(object):

    def get_str(self):
        pass

    def get_child_str(self, name):
        config = self.get(name)
        if config is None:
            return None
        return config.get()

    def get_int(self):
        pass

    def get(self, name):
        pass

    def get_bool(self):
        return False

    def get_child_bool(self, name):
        config = self.get(name)
        if config is None:
            return None
        return config.get_bool()

    def get_child_int(self, name):
        config = self.get(name)
        if config is None:
            return None
        return config.get_int()

    def get_child_dict(self, name):
        config = self.get(name)
        if config is None:
            return None
        return config.get_dict()

    def get_elem(self, index):
        pass

    def get_size(self, index):
        pass

    def get_from_list(self, name_list):
        pass

    def merge(self, new_value):
        return new_value

    def get_tree(self, config, interpret=False, path=None):
        if type(config) == list:
            return config_array(config)
        elif type(config) == dict or type(config) == OrderedDict:
            return config_object(config, interpret, path)
        elif type(config) == str:
            return config_string(config)
        elif type(config) == bool:
            return config_bool(config)
        else:
            return config_number(config)

    def get_string(self):
        return self.dump_to_string()

    def dump_to_string(self, indent=2):
        if indent is not None:
            return json.dumps(self.get_dict(), indent=indent)
        else:
            return json.dumps(self.get_dict())


class config_object(config):

    def __init__(self, config, interpret=False, path=None):
        self.items = OrderedDict()

        for key, value in config.items():

            if interpret and key == 'includes':
                for include in value:
                    self.merge(import_config_from_file(include, interpret=interpret, find=True, path=path))

            else:
                if self.items.get(key) is not None:
                    self.items[key] = self.items[key].merge(self.get_tree(value, interpret, path))
                else:
                    self.items[key] = self.get_tree(value, interpret, path)

    def merge(self, new_value):
        for key, value in new_value.items.items():
            if self.items.get(key) is None:
                self.items[key] = value
            else:
                self.items[key] = self.items[key].merge(value)

        return self

    def get_from_list(self, name_list):
        if len(name_list) == 0:
            return self

        result = None
        name_pos = 0

        name = None
        for item in name_list:
            if item != "*" and item != "**":
                name = item
                break
            name_pos += 1

        for key, value in self.items.items():
            if name == key:
                result = value.get_from_list(name_list[name_pos + 1:])
                if name_pos == 0 or result is not None:
                    return result
            elif name_list[0] == "*":
                result = value.get_from_list(name_list[1:])
                if result is not None:
                    return result
            elif name_list[0] == "**":
                result = value.get_from_list(name_list)
                if result is not None:
                    return result

        return result

    def set_from_list(self, name_list, value):
        key = name_list.pop(0)
        if len(name_list) == 0:
            prev_value = self.items.get(key)
            new_value = self.get_tree(value) 
            if prev_value is not None:
                self.items[key] = prev_value.merge(new_value)
            else:
                self.items[key] = new_value
        else:
            if self.items.get(key) is None:
                self.items[key] = config_object(OrderedDict())
            self.items[key].set_from_list(name_list, value)


    def get(self, name):
        return self.get_from_list(name.split('/'))

    def set(self, name, value):
        self.set_from_list(name.split('/'), value)

    def user_set(self, key, value):

        # In case the path is not absolute and does not contain *
        # add it implicitly to let the user specify a property
        # without having to put **/ at the beginning
        if key[0] != '*' and key[0] != '/' and key.find('/') != -1:
            key = '**/' + key

        if key[0] == '/':
            key = key[1:]

        if key.find('/') != -1:
            root, prop = key.rsplit('/', 1)
            if self.get(root) is not None:
                self.get(root).set(prop, value)
            else:
                self.set(key, value)
        else:
            self.set(key, value)

    def get_dict(self, serialize=True):
        if serialize:
            result = {}
        else:
            result = OrderedDict()
        for key,value in self.items.items():
            result[key] = value.get_dict(serialize=serialize)
        return result

    def get_items(self):
        return self.items


class config_array(config):

    def __init__(self, config):
        self.elems = []
        for elem in config:
            self.elems.append(self.get_tree(elem))

    def get_from_list(self, name_list):
        if len(name_list) == 0:
            return self
        return None

    def get_size(self):
        return len(self.elems)

    def get_elem(self, index):
        return self.elems[index]

    def get_dict(self, serialize=True):
        result = []
        for elem in self.elems:
            result.append(elem.get_dict(serialize=serialize))
        return result

    def get(self):
        return self.elems

    def merge(self, new_value):
        if type(new_value) != config_array:
            new_value = config_array([new_value.get_dict()])

        for elem in new_value.elems:
            self.elems.append(elem)

        return self


class config_string(config):

    def __init__(self, config):
        self.value = config

    def get_from_list(self, name_list):
        if len(name_list) == 0:
            return self
        return None

    def get(self):
        return self.value

    def get_bool(self):
        return self.value == 'True' or self.value == 'true'

    def get_dict(self, serialize=True):
        return self.value

    def get_int(self):
        return int(self.get(), 0)


class config_number(config):

    def __init__(self, config):
        self.value = config

    def get_from_list(self, name_list):
        if len(name_list) == 0:
            return self
        return None

    def get(self):
        return self.value

    def get_dict(self, serialize=True):
        return self.value

    def get_int(self):
        return self.get()


class config_bool(config):

    def __init__(self, config):
        self.value = config

    def get_from_list(self, name_list):
        if len(name_list) == 0:
            return self
        return None

    def get(self):
        return self.value

    def get_dict(self, serialize=True):
        return self.value

    def get_bool(self):
        return self.get()
