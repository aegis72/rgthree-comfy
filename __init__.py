"""
@author: rgthree
@title: Comfy Nodes
@nickname: rgthree
@description: A bunch of nodes I created that I also find useful.
"""

import glob
import json
import os
import shutil
import re

from .config import RGTHREE_CONFIG

# from .server import server

from .py.log import log_welcome
from .py.context import RgthreeContext
from .py.context_switch import RgthreeContextSwitch
from .py.context_switch_big import RgthreeContextSwitchBig
from .py.display_any import RgthreeDisplayAny, RgthreeDisplayInt
from .py.lora_stack import RgthreeLoraLoaderStack
from .py.seed import RgthreeSeed
from .py.sdxl_empty_latent_image import RgthreeSDXLEmptyLatentImage
from .py.power_prompt import RgthreePowerPrompt
from .py.power_prompt_simple import RgthreePowerPromptSimple
from .py.image_inset_crop import RgthreeImageInsetCrop
from .py.context_big import RgthreeBigContext
from .py.ksampler_config import RgthreeKSamplerConfig
from .py.sdxl_power_prompt_postive import RgthreeSDXLPowerPromptPositive
from .py.sdxl_power_prompt_simple import RgthreeSDXLPowerPromptSimple
from .py.any_switch import RgthreeAnySwitch

NODE_CLASS_MAPPINGS = {
  RgthreeBigContext.NAME: RgthreeBigContext,
  RgthreeContext.NAME: RgthreeContext,
  RgthreeContextSwitch.NAME: RgthreeContextSwitch,
  RgthreeContextSwitchBig.NAME: RgthreeContextSwitchBig,
  RgthreeDisplayInt.NAME: RgthreeDisplayInt,
  RgthreeDisplayAny.NAME: RgthreeDisplayAny,
  RgthreeLoraLoaderStack.NAME: RgthreeLoraLoaderStack,
  RgthreeSeed.NAME: RgthreeSeed,
  RgthreeImageInsetCrop.NAME: RgthreeImageInsetCrop,
  RgthreePowerPrompt.NAME: RgthreePowerPrompt,
  RgthreePowerPromptSimple.NAME: RgthreePowerPromptSimple,
  RgthreeKSamplerConfig.NAME: RgthreeKSamplerConfig,
  RgthreeSDXLEmptyLatentImage.NAME: RgthreeSDXLEmptyLatentImage,
  RgthreeSDXLPowerPromptPositive.NAME: RgthreeSDXLPowerPromptPositive,
  RgthreeSDXLPowerPromptSimple.NAME: RgthreeSDXLPowerPromptSimple,
  RgthreeAnySwitch.NAME: RgthreeAnySwitch,
}


# This doesn't import correctly..
# WEB_DIRECTORY = "./web"

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DIR_DEV_WEB = os.path.abspath(f'{THIS_DIR}/web/')
DIR_PY = os.path.abspath(f'{THIS_DIR}/py')

# remove old directory.
OLD_DIR_WEB = os.path.abspath(f'{THIS_DIR}/../../web/extensions/rgthree')
if os.path.exists(OLD_DIR_WEB):
  shutil.rmtree(OLD_DIR_WEB)

DIR_WEB = os.path.abspath(f'{THIS_DIR}/../../web/extensions/rgthree-comfy')
if os.path.exists(DIR_WEB):
  shutil.rmtree(DIR_WEB)
os.makedirs(DIR_WEB)

shutil.copytree(DIR_DEV_WEB, DIR_WEB, dirs_exist_ok=True)


def extend_config(default_config, user_config):
  cfg = {}
  for key, value in default_config.items():
    if key not in user_config:
      cfg[key] = value
    elif isinstance(value, dict):
      cfg[key] = extend_config(value, user_config[key])
    else:
      cfg[key] = user_config[key] if key in user_config else value
  return cfg


with open(os.path.join(DIR_WEB, 'rgthree_config.js'), 'w', encoding = 'UTF-8') as file:
  file.write('export const rgthreeConfig = ' + json.dumps(RGTHREE_CONFIG))

# shutil.copy(os.path.join(THIS_DIR, 'rgthree_config.json'), os.path.join(DIR_WEB, 'rgthree_config.js'))


NOT_NODES = ['constants', 'log', 'utils', 'rgthree']

__all__ = ['NODE_CLASS_MAPPINGS']

nodes = []
for file in glob.glob('*.py', root_dir=DIR_PY) + glob.glob('*.js', root_dir=os.path.join(DIR_DEV_WEB, 'js')):
  name = os.path.splitext(file)[0]
  if name not in nodes and name not in NOT_NODES and not name.startswith(
      '_') and not name.startswith('base') and not 'utils' in name:
    nodes.append(name)

log_welcome(num_nodes=len(nodes))


# Alright, I don't like doing this, but until https://github.com/comfyanonymous/ComfyUI/issues/1502
# and/or https://github.com/comfyanonymous/ComfyUI/pull/1503 is pulled into ComfyUI, we need a way
# to optimize the recursion that happens on prompt eval. This is particularly important for
# rgthree nodes because workflows can contain many context nodes, but the problem would exist for
# other nodes' (like "pipe" nodes, efficieny nodes). With `Context Big` nodes being
# introduced, the number of input recursion that happens in these methods is exponential with a
# saving of 1000's of percentage points over.
if 'patch_recursive_execution' in RGTHREE_CONFIG and RGTHREE_CONFIG['patch_recursive_execution']:
  import execution

  msg = "\33[32m[rgthree] Optimizing ComfyUI recursive execution. \33[33mIf queueing and/or re-queueing seems "
  msg += "broken, change \"patch_recursive_execution\" to false in rgthree_config.json \33[0m"
  print(msg)

  class RgthreePatchRecursiveExecute_Set_patch_recursive_execution_to_false_if_not_working:
    """A fake 'list' that the caller for recursive_will_execute expects but we override such that
    `len(inst)` will return the count number, and `inst[-1]` will return the unique_id. Since that
    all the caller cares about, we can save several minutes and many MB of ram by simply counting
    numbers instead of concatenating a list of millions (only to count it). However the caller
    expects such a list, so we fake it with this.

    This mimics the enhancement from https://github.com/rgthree/ComfyUI/commit/50b3fb1 but without
    modifying the execution.py
    """
    def __init__(self, unique_id):
      self.unique_id = unique_id
      self.count = 0

    def add(self, value):
      self.count += value

    def __getitem__(self, key):
      """Returns the `unique_id` with '-1' since that's what the caller expects."""
      if key == -1:
        return self.unique_id
      # This one would future proof the proposed changes, in that case "0" is the count
      if key == 0:
        return self.count
      else:
        return -1

    def __len__(self):
      """Returns the "count" of the "list" as if we were building up a list instea of just
      incrementing `count`.
      """
      print('yoyo')
      return self.count

    # The following (hopefully) future proofs if https://github.com/rgthree/ComfyUI/commit/50b3fb1
    # goes in, which changes from using `len` on a list, to sort directly (and, thus "<" and ">").
    def __gt__(self, other):
      return self.count > other

    def __lt__(self, other):
      return self.count < other

    def __str__(self):
      return str((self.count, self.unique_id,))


  execution.rgthree_cache_recursive_output_delete_if_changed_output = {}
  execution.rgthree_cache_recursive_will_execute = {}

  def rgthree_execute(self, *args, **kwargs):
    # When we execute, we'll reset our global cache here.
    execution.rgthree_cache_recursive_output_delete_if_changed_output = {}
    execution.rgthree_cache_recursive_will_execute = {}
    return self.old_execute(*args, **kwargs)


  def rgthree_recursive_will_execute(prompt, outputs, current_item, *args, **kwargs):
    unique_id = current_item
    inputs = prompt[unique_id]['inputs']
    will_execute = RgthreePatchRecursiveExecute_Set_patch_recursive_execution_to_false_if_not_working(unique_id)
    if unique_id in outputs:
        return will_execute

    will_execute.add(1)
    for x in inputs:
        input_data = inputs[x]
        if isinstance(input_data, list):
          input_unique_id = input_data[0]
          output_index = input_data[1]
          node_output_cache_key = f'{input_unique_id}.{output_index}'
          will_execute_value = None
          # If this node's output has already been recursively evaluated, then we can reuse.
          if node_output_cache_key in execution.rgthree_cache_recursive_will_execute:
            will_execute_value = execution.rgthree_cache_recursive_will_execute[node_output_cache_key]
          elif input_unique_id not in outputs:
            will_execute_value = execution.recursive_will_execute(prompt, outputs, input_unique_id, *args, **kwargs)
            execution.rgthree_cache_recursive_will_execute[node_output_cache_key] = will_execute_value
          if will_execute_value is not None:
            will_execute.add(len(will_execute_value))
    return will_execute


  def rgthree_recursive_output_delete_if_changed(prompt, old_prompt, outputs, current_item, *args, **kwargs):
    unique_id = current_item
    inputs = prompt[unique_id]['inputs']
    class_type = prompt[unique_id]['class_type']
    class_def = execution.nodes.NODE_CLASS_MAPPINGS[class_type]

    is_changed_old = ''
    is_changed = ''
    to_delete = False
    if hasattr(class_def, 'IS_CHANGED'):
      if unique_id in old_prompt and 'is_changed' in old_prompt[unique_id]:
        is_changed_old = old_prompt[unique_id]['is_changed']
      if 'is_changed' not in prompt[unique_id]:
        input_data_all = execution.get_input_data(inputs, class_def, unique_id, outputs)
        if input_data_all is not None:
          try:
            #is_changed = class_def.IS_CHANGED(**input_data_all)
            is_changed = execution.map_node_over_list(class_def, input_data_all, "IS_CHANGED")
            prompt[unique_id]['is_changed'] = is_changed
          except:
            to_delete = True
      else:
        is_changed = prompt[unique_id]['is_changed']

    if unique_id not in outputs:
      return True

    if not to_delete:
      if is_changed != is_changed_old:
        to_delete = True
      elif unique_id not in old_prompt:
        to_delete = True
      elif inputs == old_prompt[unique_id]['inputs']:
        for x in inputs:
          input_data = inputs[x]

          if isinstance(input_data, list):
            input_unique_id = input_data[0]
            output_index = input_data[1]
            node_output_cache_key = f'{input_unique_id}.{output_index}'
            # If this node's output has already been recursively evaluated, then we can stop.
            if node_output_cache_key in execution.rgthree_cache_recursive_output_delete_if_changed_output:
              to_delete = execution.rgthree_cache_recursive_output_delete_if_changed_output[
                node_output_cache_key]
            elif input_unique_id in outputs:
              to_delete = execution.recursive_output_delete_if_changed(prompt, old_prompt, outputs,
                                                                      input_unique_id, *args, **kwargs)
              execution.rgthree_cache_recursive_output_delete_if_changed_output[
                node_output_cache_key] = to_delete
            else:
              to_delete = True
            if to_delete:
              break
      else:
        to_delete = True

    if to_delete:
      d = outputs.pop(unique_id)
      del d
    return to_delete


  execution.PromptExecutor.old_execute = execution.PromptExecutor.execute
  execution.PromptExecutor.execute = rgthree_execute

  execution.old_recursive_output_delete_if_changed = execution.recursive_output_delete_if_changed
  execution.recursive_output_delete_if_changed = rgthree_recursive_output_delete_if_changed

  execution.old_recursive_will_execute = execution.recursive_will_execute
  execution.recursive_will_execute = rgthree_recursive_will_execute


print()