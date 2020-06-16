
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

import plptools as plp

class SystemConfigDesc(object):

  def __init__(self, configString):

    self.properties = {}
    self.items = {}
    self.name = configString

    for item in configString.split(':'):
      key, value = item.split('=')
      if key.find('prop@') != -1:
        key = key.replace('prop@', '')
        self.properties[key] = value
      else:
        self.items[key] = value

  def __str__(self):
    return self.name
            
class SystemConfigDescSet(object):

  def __init__(self, configString):

    self.configs = []

    for config in configString.split(';'):
      self.configs.append(SystemConfigDesc(config))


class Attr(object):
  def __init__(self, name):
    self.name = name


class Mmap(Attr):

  def __init__(self, base, size, name='mmap'):
    super(Mmap, self).__init__(name)
    self.base = base
    self.size = size

  def dump(self, indent):
    print (indent + 'mmap = [0x%x:0x%x]' % (self.base, self.base + self.size))


class ConfigItem(object):

  def __init__(self, name, parent=None, attrs=[]):
    self.properties = {}
    self.parameters = {}
    self.parent = parent
    self.childs = []
    self.name = name
    self.attrs = attrs
    for attr in self.attrs:
      self.__dict__[attr.name] = attr
    if parent != None: parent.__reg_child(self)

  def add_parameter(self, name, value):
    self.parameters[name] = value

  def set_parameter(self, name, value):
    if self.parameters.get(name) != None:
      self.parameters[name] = value

  def get_parameter(self, name, down=False):

    value = self.parameters.get(name)
    if value != None: return value
    if down:
      for child in self.childs:
        value = child.get_parameter(name, down)
        if value != None: return value
    else:
      if self.parent != None: return self.parent.get_parameter(name)
    return None

  def set_value(self, value):
    self.value = value

  def __reg_child(self, child):
    self.childs.append(child)
    self.properties[child.name] = child

  def build(self):
    pass

  def set(self, **kwargs):
    self.properties.update(kwargs)
    self.__dict__.update(kwargs)

  def get_property_from_path(self, name):

    name_list = name.split('/')
    name_first = name_list[0]

    for key, prop in self.properties.items():
      if name_first == key:
        if len(name_list) == 1: return prop
        else: return prop.get_property_from_path('/'.join(name_list[1:]))

      try:
        value = prop.get_property_from_path(name)
        if value != None: return value
      except:
        pass

    if len(name_list) == 1:
      for key, prop in self.parameters.items():
        if key == name_first: return prop

    return None


  def get(self, name, down=False, fullName=''):

    fullName = fullName + '/' + self.name

    if name.find('.') != -1:
      path, prop = name.split('.')
      if fullName.rfind(path) == len(fullName) - len(path):
        value = self.properties.get(prop)
        if value != None: return value

    value = self.properties.get(name)
    if value != None: return value

    if down:
      for child in self.childs:
        value = child.get(name, down, fullName=fullName)
        if value != None: return value

    return None

  def dump_tree(self, indent=''):

    for attr in self.attrs:
      attr.dump(indent)

    for key, value in self.parameters.items():
      print (indent + '%s = %s' % (key, value))

    for key, value in self.properties.items():
      print (indent + '%s = %s' % (key, value))

    for child in self.childs:
      print (indent + child.name)
      child.dump_tree(indent + '  ')

class ConfigItemNoDesc(ConfigItem):

  def __init__(self, name):
    super(ConfigItemNoDesc, self).__init__(name)


class SystemConfigItem(object):

  def __init__(self, name, check_values=True):
    self.default_value = None
    self.values = {}
    self.hasValues = {}
    self.name = name
    self.check_values = check_values

  def add_value(self, value, desc):
    if desc == None: desc = ConfigItemNoDesc(value)
    else: desc = desc(value)
    desc.set_value(value=value)
    self.values[value] = desc
    self.hasValues[value] = True
    if self.default_value == None: self.default_value = desc

  def check_value(self, value):
    if not self.check_values: return True
    return self.hasValues.get(value) != None

  def get_desc(self, value):
    return self.values.get(value)

  def get_default_value(self):
    return self.default_value



class SystemConfig(object):
  """
  Class for Pulp configurations

  An instance of this class is representating one Pulp configuration
  and contains the values for each parameter.
  """

  def __init__(self):
    self.items = {}
    self.name = None

  def get_name_from_items(self, items):
    itemList = []
    for item in items:
      value = self.items.get(item)
      if value == None: continue
      itemList.append("%s=%s" % (item, value.value))
    return ":".join(itemList)

  def get_name(self):
    """
    Return a printable description of the configuration
    This is the name of the configuration if it is given or all the properties put together
    """
    if self.name != None: return self.name
    else: return self.get_name_from_items(self.items.values())

  def add_item(self, name, value):
    self.items[name] = value

  def get_item(self, name):
    return self.items.get(name)

  def get(self, name):
    return self.get_property(name, down=True)

  def get_property(self, name, down=False):
    for key, item in self.items.items():

      if name == key: return item.value

      value = item.get_parameter(name, down)
      if value != None: return value
      value = item.get(name, down)
      if value != None: return value

    return None

  def get_property_from_path(self, name):

    for key, item in self.items.items():

      value = item.get_property_from_path(name)
      if value != None: return value

    return None

  def dump_tree(self, indent=''):
    for key, value in self.items.items():
      print (indent + '%s: %s' % (key, value.name))
      value.dump_tree(indent + '  ')

  def build(self):
    for item in self.items.values():
      item.build()

  def set_name(self, name):
    self.name = name



class SystemConfigSet(object):

  def __init__(self):
    self.items = {}

  def add_item(self, name, check_values=True):
    self.items[name] = SystemConfigItem(name, check_values)

  def add_itemValue(self, name, value, desc=None):
    self.items.get(name).add_value(value, desc)

  def set_defaults(self, config):
    for key, value in self.items.items():
      config.add_item(key, value.get_default_value())

  def get_configs(self, configString):
    configs = []
    configDescSet = SystemConfigDescSet(configString)

    for configDesc in configDescSet.configs:
      config = SystemConfig()
      configs.append(config)

      self.set_defaults(config)

      for name, value in configDesc.items.items():
        if not name in self.items: raise Exception(plp.bcolors.FAIL + 'Unknown configuration item: ' + name + plp.bcolors.ENDC)
        if not self.items.get(name).check_value(value): raise Exception(plp.bcolors.FAIL + 'Unknown configuration item value: %s=%s' % (name, value) + plp.bcolors.ENDC)
        desc = self.items.get(name).get_desc(value)
        config.add_item(name, desc)

      config.set_name(configDesc.__str__())
      config.build()

      #for name, value in configDesc.properties.items():
      #  print ('ADD')
      #  config.add_property(name, value)


    return configs



class Config(object):

  def __init__(self, decorators={}):
    self.decorators = decorators
    self.classesMap = {}
    for key,value in self.decorators.items():
      if key == 'classes': self.classesMap = value

  def hasIp(self, name):
    return self.versions.get(name) != None

  def getClass(self, name):
    return self.classes.get(name)

  def getName(self, name):
    return name

  def getMmap(self, name):
    return self.mmaps.get(name)

  def get(self, name):
    result = self.versions.get(name)
    if result != None: return result
    else: return self.properties.get(name)


class ConfigSet(object):

  def __init__(self, chips):
    self.configs = []
    self.__load_chip_configs(chips)
