"""Standard-library checks; full ADF tests use a locally supplied original."""
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch as mock_patch

import patch

ROOT = Path(__file__).resolve().parent
SOURCE = Path(os.environ.get('SR2_DISK1', ROOT / 'originals/SR2AMIGA_DISK1.adf'))


class PatcherUnitTests(unittest.TestCase):
    def test_embedded_release_matches_source_manifest(self):
        manifest = json.loads((ROOT / 'src/patches.json').read_text())
        self.assertEqual(manifest['release_version'], '1.5.0')
        self.assertEqual(patch.VERSION, manifest['release_version'])
        self.assertEqual(patch.SOURCE_PROGRAM_SHA256, manifest['source']['sha256'])

        expected_patches = tuple(
            (int(item['file_offset'], 0), bytes.fromhex(item['expected_hex']),
             bytes.fromhex(item['replacement_hex']))
            for item in manifest['patches']
        )
        self.assertEqual(patch.PROGRAM_PATCHES, expected_patches)

        expected_sizes = []
        expected_payload_offsets = []
        embedded_payloads = dict(patch.HUNK_PAYLOADS)
        for growth in manifest['hunk_growths']:
            with self.subTest(hunk=growth['hunk']):
                original_size = int(growth['original_size'], 0)
                patched_size = int(growth['patched_size'], 0)
                self.assertEqual(original_size % 4, 0)
                self.assertEqual(patched_size % 4, 0)
                for name in ('hunk_header_table_file_offset', 'hunk_record_size_file_offset'):
                    expected_sizes.append((int(growth[name], 0), original_size // 4,
                                           patched_size // 4))
                offset = int(growth['payload_file_offset'], 0)
                expected_payload_offsets.append(offset)
                payload = embedded_payloads[offset]
                self.assertEqual(payload, getattr(patch, f"PAYLOAD_{growth['hunk']}"))
                self.assertEqual(len(payload), growth['payload_size'])
                self.assertEqual(len(payload), patched_size - original_size)
                self.assertEqual(patch.sha256(payload), growth['payload_sha256'])
                self.assertTrue((ROOT / 'src' / growth['payload_source']).is_file())

        self.assertEqual(patch.HUNK_SIZE_PATCHES, tuple(expected_sizes))
        self.assertEqual([offset for offset, _ in patch.HUNK_PAYLOADS],
                         sorted(expected_payload_offsets, reverse=True))

    def test_cli_version(self):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'patch.py'), '--version'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'patch.py 1.5.0')

    def test_startup_banner_matches_release(self):
        days, minutes, ticks = patch.RELEASE_TIMESTAMP
        release_date = datetime(1978, 1, 1) + timedelta(
            days=days, minutes=minutes, seconds=ticks / 50)
        self.assertIn(f'patch {patch.VERSION} by Timo Heimonen'.encode(),
                      patch.STARTUP_SEQUENCE)
        self.assertIn(release_date.strftime('%d.%m.%Y').encode(),
                      patch.STARTUP_SEQUENCE)

    def test_reject_unknown_images(self):
        for image in (b'', bytes(patch.ADF_SIZE), bytes(patch.ADF_SIZE - 1)):
            with self.subTest(size=len(image)):
                with self.assertRaises(patch.PatchError):
                    patch.build_patched_adf(image)

    def test_reject_unknown_program(self):
        with self.assertRaises(patch.PatchError):
            patch.patch_program(bytes(270116))

    def test_atomic_output_requires_force(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'disk.adf'
            patch.write_atomic(path, b'first', False)
            with self.assertRaises(patch.PatchError):
                patch.write_atomic(path, b'second', False)
            self.assertEqual(path.read_bytes(), b'first')
            patch.write_atomic(path, b'second', True)
            self.assertEqual(path.read_bytes(), b'second')
            self.assertEqual(list(Path(temporary).iterdir()), [path])

    def test_default_name(self):
        self.assertEqual(patch.default_output_path(Path('/tmp/original.adf')).name,
                         'StreetRod2-KS31-AGA-060-Disk1.adf')


@unittest.skipUnless(SOURCE.is_file(), 'Provide originals/SR2AMIGA_DISK1.adf or SR2_DISK1')
class OriginalImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_bytes()
        cls.result = patch.build_patched_adf(cls.source)

    def test_reproducible_1_5_0_release(self):
        self.assertEqual(patch.sha256(self.result),
                         '7360096c9845b71470dad2be50c5ee351e48b2b96c00aaf6dc97ebd70057a02c')
        self.assertEqual(patch.build_patched_adf(self.source), self.result)
        result = patch.OFSImage(self.result)
        program = result.read_file('STREET_ROD').data
        # Hash of the separately built, accepted KS3.1/AGA 1.5.0 executable.
        self.assertEqual(patch.sha256(program),
                         'cc3ee220a243aa887e8f8376c61231d8d85649834c5129da4e53b276f1fdc626')
        self.assertEqual(program[0x1195a:0x1195e], bytes.fromhex('0240007f'))
        self.assertNotIn(bytes.fromhex('103900bfe2010040008013c000bfe201'), program)
        self.assertEqual(result.read_file('s/startup-sequence').data, patch.STARTUP_SEQUENCE)
        self.assertNotIn(b'SR2_060Gate', patch.STARTUP_SEQUENCE)

    def test_original_assets_and_boot_code_preserved(self):
        original = patch.OFSImage(self.source)
        result = patch.OFSImage(self.result)
        self.assertEqual(self.result[:1024], self.source[:1024])
        # Inspect every original file header, not just the trainer save.
        checked = 0
        for block_number in range(2, patch.ADF_BLOCKS):
            block = original._read_block(block_number)
            if (patch._get_long(block, 0) != patch.T_HEADER
                    or patch._get_long(block, -1) != patch.ST_FILE
                    or patch._get_long(block, 1) != block_number
                    or patch._block_sum(block) != 0):
                continue
            components = [patch._get_bstr(block, -20, 30).decode('ascii')]
            parent = patch._get_long(block, -3)
            seen = set()
            while parent != patch.ROOT_BLOCK:
                self.assertNotIn(parent, seen)
                seen.add(parent)
                directory = original._read_block(parent)
                components.insert(0, patch._get_bstr(directory, -20, 30).decode('ascii'))
                parent = patch._get_long(directory, -3)
            name = '/'.join(components)
            # Ignore stale headers outside the live directory tree.
            try:
                live = original.find_path(name)
            except patch.PatchError:
                continue
            if live.block_number != block_number:
                continue
            if name.lower() not in ('street_rod', 's/startup-sequence'):
                self.assertEqual(original.read_file(name).data, result.read_file(name).data, name)
                checked += 1
        self.assertGreater(checked, 10)

    def test_modified_source_rejected(self):
        damaged = bytearray(self.source)
        damaged[12345] ^= 1
        with self.assertRaises(patch.PatchError):
            patch.build_patched_adf(bytes(damaged))
        with self.assertRaises(patch.PatchError):
            patch.build_patched_adf(self.result)

    def test_corrupt_road_swap_payload_rejected(self):
        # HUNK_PAYLOADS captures the bytes used by patch_program; replacing only
        # PAYLOAD_10 would leave that actual insertion input unchanged.
        payloads = tuple(
            (offset, bytes([payload[0] ^ 1]) + payload[1:])
            if offset == 0xa554 else (offset, payload)
            for offset, payload in patch.HUNK_PAYLOADS
        )
        self.assertNotEqual(payloads, patch.HUNK_PAYLOADS)
        with mock_patch.object(patch, 'HUNK_PAYLOADS', payloads):
            with self.assertRaisesRegex(patch.PatchError,
                                        'internal STREET_ROD result verification failed'):
                patch.build_patched_adf(self.source)

    def test_cli_preserves_source_and_existing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'source.adf'
            output = Path(temporary) / 'result.adf'
            source.write_bytes(self.source)
            command = [sys.executable, '-B', str(ROOT / 'patch.py'), str(source), '-o', str(output)]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(output.read_bytes(), self.result)
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(second.returncode, 1)
            self.assertIn('already exists', second.stderr)
            self.assertEqual(output.read_bytes(), self.result)
            same = subprocess.run(command[:-1] + [str(source), '--force'], capture_output=True, text=True)
            self.assertEqual(same.returncode, 1)
            self.assertIn('must be different', same.stderr)
            self.assertEqual(source.read_bytes(), self.source)
            self.assertEqual(subprocess.run(command + ['--force'], capture_output=True).returncode, 0)


if __name__ == '__main__':
    unittest.main()
