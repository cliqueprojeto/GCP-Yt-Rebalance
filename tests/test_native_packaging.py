import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("native_contract",ROOT/"scripts/native_contract.py")
contract=importlib.util.module_from_spec(spec); spec.loader.exec_module(contract)


class NativePackagingTests(unittest.TestCase):
    def test_architectures_distinguish_linux_and_macos(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"artifacts/unit-temp") as directory:
            path=Path(directory)/"binary"
            elf=bytearray(64); elf[:6]=b"\x7fELF\x02\x01"; struct.pack_into("<H",elf,18,62)
            path.write_bytes(elf); self.assertEqual(contract.architectures(path),{"linux-x86_64"})
            path.write_bytes(b"\xcf\xfa\xed\xfe"+struct.pack("<I",0x0100000c)+bytes(24))
            self.assertEqual(contract.architectures(path),{"macos-arm64"})
            path.write_bytes(b"\xca\xfe\xba\xbe"+struct.pack(">I",2)+struct.pack(">IIIII",0x01000007,0,48,8,0)+struct.pack(">IIIII",0x0100000c,0,56,8,0)+bytes(16))
            self.assertEqual(contract.architectures(path),{"macos-x86_64","macos-arm64"})

    def test_rejects_non_native_and_truncated_headers(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"artifacts/unit-temp") as directory:
            path=Path(directory)/"binary"
            for content in (b"MZWindows binary",b"\xca\xfe\xba\xbe",b"\x7fELF\x01\x01"+bytes(20)):
                path.write_bytes(content)
                with self.assertRaises(ValueError): contract.architectures(path)

    def test_installed_payload_must_match(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"artifacts/unit-temp") as directory:
            root=Path(directory); (root/"model").write_bytes(b"original")
            original=contract.manifest(root)
            contract.verify_manifest(root,original)
            (root/"model").write_bytes(b"damaged")
            with self.assertRaises(ValueError): contract.verify_manifest(root,original)

    def test_missing_runtime_is_not_a_complete_installer(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"artifacts/unit-temp") as directory:
            with self.assertRaises(ValueError): contract.validate_payload(directory,"macos-arm64")
