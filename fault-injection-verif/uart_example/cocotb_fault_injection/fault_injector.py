import os
import logging
import re

import cocotb
from cocotb.handle import ModifiableObject, RegionObject, NonHierarchyIndexableObject
from cocotb.handle import Force, Release
from cocotb.triggers import Timer
from cocotb.log import SimLog, SimLogFormatter, SimTimeContextFilter

from .yosys_if import AnalyzedRTLDesign
from .strategy import _SET, _SEU


class FaultInjector:
    def __init__(self, mttf_timer=None, transient_duration_timer=None,
                 injection_strategy=None, injection_goal=None,
                 count_handle=None, name_handle=None, leaf_module_info=None,
                 name=None, log_level=logging.INFO, log_file=None,
                 max_signal_len=128, injection_goal_check=1):

        self._name = name or "default"
        self._log = SimLog(f"{self.__class__.__name__}.{self._name}")
        self._log.setLevel(log_level)
        self._seelog = SimLog(f"{self.__class__.__name__}.{self._name}_see")
        self._seelog.setLevel(log_level)

        if log_file is not None:
            fh = logging.FileHandler(log_file, mode='w')
            fh.addFilter(SimTimeContextFilter())
            fh.setFormatter(SimLogFormatter())
            self._log.addHandler(fh)
            self._seelog.addHandler(fh)
            self._seelog.propagate = False

        self._faults = 0
        self._see_id = 0
        self._max_signal_len = max_signal_len
        self._injection_goal_check = injection_goal_check

        self._mttf_timer = mttf_timer
        self._transient_duration_timer = transient_duration_timer
        self._injection_strategy = injection_strategy
        self._injection_goal = injection_goal

        self._leaf_module_info = leaf_module_info or {}
        self._seu_signals = []
        self._set_signals = []

        self._count_handle = count_handle
        self._name_handle = name_handle

        self._disabled = False
        if os.getenv("SEE", "1") == "0":
            self._log.info("Fault injection disabled by environment settings.")
            self._disabled = True
            return

        if os.getenv("NETLIST", "0") == "0":
            self._rtl = AnalyzedRTLDesign()
        else:
            self._log.info("Netlist simulation - skipping FF recognition.")
            self._rtl = None

        if cocotb.SIM_NAME.lower().startswith("icarus"):
            self._log.warning("Using RMW-based SETs (not ideal).")
            self._put_set = self._put_set_rmw
            self._unput_set = self._unput_set_rmw
        else:
            self._put_set = self._put_set_force
            self._unput_set = self._unput_set_release

    def _put_seu(self, see):
        try:
            if see.signal_spec["type"] == "reg":
                modval = int(see.signal_spec["handle"].value) ^ (1 << see.signal_index)
                see.signal_spec["handle"].value = modval
            elif see.signal_spec["type"] == "prim":
                see.signal_spec["prim_handle"].value = 1
        except ValueError:
            self._seelog.warning('Skipped undefined signal (%s)', see.signal_spec["handle"]._path)

    def _put_set_force(self, see):
        try:
            if see.signal_handle._range is None:
                val = int(see.signal_handle)
                see.signal_handle.value = Force(not val)
            else:
                val = int(see.signal_handle[see.signal_index])
                see.signal_handle[see.signal_index].value = Force(not val)
        except ValueError:
            self._seelog.warning("SET force skipped on undefined signal (%s)", see.signal_handle._path)

    def _unput_set_release(self, see):
        if see.signal_handle._range is None:
            see.signal_handle.value = Release()
        else:
            see.signal_handle[see.signal_index].value = Release()

    def _put_set_rmw(self, see):
        try:
            val = int(see.signal_handle.value)
            see.oldval = val & (1 << see.signal_index)
            see.signal_handle.value = val ^ (1 << see.signal_index)
        except ValueError:
            self._seelog.warning("Skipped undefined RMW SET on (%s)", see.signal_handle._path)

    def _unput_set_rmw(self, see):
        try:
            val = int(see.signal_handle.value)
            if val & (1 << see.signal_index) != see.oldval:
                see.signal_handle.value = val ^ (1 << see.signal_index)
        except ValueError:
            self._seelog.warning("Could not recover RMW SET on (%s)", see.signal_handle._path)

    async def _inject_faults(self, fault_spec):
        seu_list = []
        set_list = []

        for see in fault_spec:
            if isinstance(see, _SET):
                if len(see.signal_handle) <= self._max_signal_len:
                    set_list.append(see)
            elif isinstance(see, _SEU):
                if len(see.signal_spec["handle"]) > self._max_signal_len:
                    continue
                seu_list.append(see)

        await self._mttf_timer

        self._see_id += 1
        self._faults += len(seu_list) + len(set_list)

        see_id_str = ""
        for see in seu_list:
            see_id_str += f"SEU_{see.signal_spec['handle']._path}[{see.signal_index}] "
            self._seelog.info("SEE ID %d: SEU in %s[%d].", self._see_id,
                              see.signal_spec["handle"]._path, see.signal_index)
            self._put_seu(see)

        for see in set_list:
            see_id_str += f"SET_{see.signal_handle._path}[{see.signal_index}] "
            self._seelog.info("SEE ID %d: SET in %s[%d].", self._see_id,
                              see.signal_handle._path, see.signal_index)
            self._put_set(see)

        if self._count_handle:
            self._count_handle.value = self._see_id
        if self._name_handle:
            self._name_handle.value = see_id_str

        if self._transient_duration_timer is not None:
            await self._transient_duration_timer
            for see in set_list:
                self._unput_set(see)

    async def start(self):
        self._running = True
        if self._disabled:
            return

        self._injection_strategy.initialize(self._seu_signals, self._set_signals)
        self._log.info("Starting SEE injection.")
        self._log.info("SEU candidates: %d, SET candidates: %d",
                       len(self._seu_signals), len(self._set_signals))

        see_gen = iter(self._injection_strategy)

        while not self._injection_goal.eval(self._faults, len(self._seu_signals) + len(self._set_signals)) and self._running:
            for _ in range(self._injection_goal_check):
                see_list = next(see_gen)
                await self._inject_faults(see_list)
                if not self._running:
                    break

        self._log.info("SEE injection complete.")
        self._running = False

    def stop(self):
        self._running = False

    async def join(self):
        while self._running:
            await Timer(1, "us")

    def print_summary(self):
        self._log.info("Injected %d SEEs into %d nodes.", self._faults,
                       len(self._seu_signals) + len(self._set_signals))


class HierarchyFaultInjector(FaultInjector):
    def __init__(self, root, exclude_names=None, exclude_paths=None, exclude_modules=None, include_names=None, **kwargs):
        super().__init__(**kwargs)
        if self._disabled:
            return

        self._exclude_names = "(" + ")|(".join(exclude_names or []) + ")" if exclude_names else "$^"
        self._exclude_paths = "(" + ")|(".join(exclude_paths or []) + ")" if exclude_paths else "$^"
        self._exclude_modules = exclude_modules or []
        self._include_names = "(" + ")|(".join(include_names or []) + ")" if include_names else ".*"

        if isinstance(root, RegionObject):
            self._traverse_hierarchy(root)
        else:
            for r in root:
                self._traverse_hierarchy(r)

    def _traverse_hierarchy(self, hier, name_ovr=None):
        mod_name = name_ovr or hier.get_definition_name()
        for handle in hier:
            if re.match(self._exclude_paths, handle._path):
                continue
            if isinstance(handle, ModifiableObject):
                if re.match(self._exclude_names, handle._name):
                    continue
                if not re.match(self._include_names, handle._name):
                    continue

                self._seu_signals.append({
                    "handle": handle,
                    "ctrl_handles": [],
                    "type": "reg"
                })
                self._set_signals.append(handle)

            elif isinstance(handle, RegionObject):
                if handle.get_definition_name() not in self._exclude_modules:
                    self._traverse_hierarchy(handle)
            elif isinstance(handle, NonHierarchyIndexableObject):
                self._traverse_hierarchy(handle, name_ovr=mod_name)
