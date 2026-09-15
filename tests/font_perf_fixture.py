"""Actual firmware execution with explicit stubs for absent XIP font banks.

The descriptor dispatcher, injected code, and decoder execute real Thumb code.
Only native font callbacks, XIP guards and cache flush are mocked. Counts are
CPU instructions, never cycles/FPS, and exclude the unavailable native banks.
"""
import hashlib
import json
import struct
from pathlib import Path

import test_thai_device_path as device
from unicorn import UC_HOOK_CODE

LOOKUP = 0x004E8D90
XIP_ENTER = 0x004760EA
XIP_EXIT = 0x00476100


class FontFixture:
    def __init__(self, artifact=None, spec=None):
        original_artifact, original_spec = device.ARTIFACT, device.SPEC
        try:
            device.ARTIFACT = Path(artifact or original_artifact)
            device.SPEC = Path(spec or original_spec)
            self.sha256 = hashlib.sha256(device.ARTIFACT.read_bytes()).hexdigest()
            assert self.sha256 == json.loads(device.SPEC.read_text())['output_sha256']
            device.ThaiDevicePathTests.setUpClass()
            self.vm = device.ThaiDevicePathTests()
            # Isolate class-level data from subsequent baseline/candidate VMs.
            for key in ("payload", "font_blob", "font_blob_address"):
                setattr(self.vm, key, getattr(device.ThaiDevicePathTests, key))
        finally:
            device.ARTIFACT, device.SPEC = original_artifact, original_spec
        self.vm.setUp()
        self.fonts = self.vm.font_arrays()
        self.callbacks = []
        self.guards = []
        self.instructions = 0
        self.flushes = 0
        self.native_result = False
        self.native_placeholder = False
        self.native_stub = self.vm.alloc(4)
        self.vm.uc.mem_write(self.native_stub, bytes.fromhex("7047"))
        self.vm.uc.hook_add(UC_HOOK_CODE, self._instruction)

    def _instruction(self, uc, address, size, _):
        self.instructions += 1
        arm = self.vm.arm_const
        if address == self.vm.flush_stub:
            self.flushes += 1
        if address in (XIP_ENTER, XIP_EXIT):
            self.guards.append(address)
            uc.reg_write(arm.UC_ARM_REG_PC, uc.reg_read(arm.UC_ARM_REG_LR))
        elif address == self.native_stub:
            args = tuple(uc.reg_read(reg) for reg in (
                arm.UC_ARM_REG_R0, arm.UC_ARM_REG_R1,
                arm.UC_ARM_REG_R2, arm.UC_ARM_REG_R3))
            self.callbacks.append(args)
            if self.native_result:
                # Deliberately distinctive metrics and short-enum flags.
                raw = struct.pack("<IHHHhhBBIIII", 0, 17, 9, 13, -2, -4,
                                  8, int(self.native_placeholder), 0, 0, 123, 0)
                uc.mem_write(args[1], raw)
            uc.reg_write(arm.UC_ARM_REG_R0, int(self.native_result))

    def chain(self, size=28, count=4, with_thai=True, runtime=True, xip=True):
        vm = self.vm
        layout = self.fonts[size]
        tail = (vm.runtime_font(layout)[0] if runtime else layout["address"]) if with_thai else 0
        native = []
        for _ in range(count):
            font = vm.alloc(36)
            # Native flags/dsc exercise the stock kerning and XIP branches.
            vm.write_words(font, [self.native_stub | 1, 0, 0, 43, 13,
                                  0, 0x80100000 if xip else 0, tail, 0])
            native.insert(0, font)
            tail = font
        return tail, native

    def lookup(self, root, codepoint, next_codepoint=0, offset=0):
        vm = self.vm
        allocation = vm.alloc(44)
        vm.uc.mem_write(allocation, b'\xa5' * 44)
        dsc = allocation + 4 + offset
        result = vm.call(LOOKUP, [root, dsc, codepoint, next_codepoint])
        assert bytes(vm.uc.mem_read(allocation, 4 + offset)) == b'\xa5' * (4 + offset)
        assert bytes(vm.uc.mem_read(dsc + 32, 4)) == b'\xa5' * 4
        return result, bytes(vm.uc.mem_read(dsc, 32))

    def counts(self):
        return dict(instructions=self.instructions, callbacks=len(self.callbacks),
                    xip_guards=len(self.guards))
