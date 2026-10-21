"""Deterministic, network-free taxi path generation and release regression tests."""
from __future__ import annotations
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.taxi_paths import build_paths, generate_paths, load_manual
from tools.generate import profile_content_fingerprint, generate_profile
from tools.data_fingerprint import fingerprint
from tools.profile_catalog import required_data_paths
from tools.release_version import is_path_update, plan_release


def path(id=6, origin=2, target=4, cost=5):
    return dict(ID=str(id), FromTaxiNode=str(origin), ToTaxiNode=str(target), Cost=str(cost))


def point(index, x, world=0, delay=0, id=6):
    return dict(PathID=str(id), NodeIndex=str(index), ContinentID=str(world),
                Loc_0=str(x), Loc_1='0', Loc_2='0', Delay=str(delay), Flags='0')


class TaxiPathTests(unittest.TestCase):
    def build(self, paths=None, points=None, manual=None):
        return build_paths(paths if paths is not None else [path()],
                           points if points is not None else [point(0, 0), point(1, 320)],
                           {2, 4, 5}, manual or {'nodes': {}}, '1.60.1.70205')

    def test_directed_geometry_and_seconds_delay(self):
        paths, report = self.build(points=[point(1, 320, delay=3), point(0, 0)])
        self.assertEqual(13, paths[6]['durationSeconds'])
        self.assertEqual(3, paths[6]['delaySeconds'])
        self.assertEqual(5, paths[6]['basePriceCopper'])
        self.assertEqual(1, report['nodes']['2']['outgoingCount'])
        self.assertEqual(0, report['nodes']['4']['outgoingCount'])

    def test_teleport_flag_excludes_the_following_jump(self):
        first = point(0, 0)
        first['Flags'] = '1'
        paths, _ = self.build(points=[first, point(1, 900000), point(2, 900032)])
        self.assertEqual(1, paths[6]['durationSeconds'])
        self.assertEqual(32, paths[6]['distanceYards'])
        self.assertTrue(paths[6]['hasTeleports'])

    def test_parallel_paths_and_excluded_endpoints(self):
        paths, report = self.build(paths=[path(), path(7, 2, 4), path(8, 4, 99), path(9, 2, 2)])
        self.assertEqual({6, 7}, set(paths))
        self.assertEqual(2, report['excludedPathCount'])

    def test_cross_world_and_missing_geometry_keep_unknown_duration(self):
        for points in ([], [point(0, 0)], [point(0, 0), point(1, 900000, world=1)],
                       [point(0, 0), point(2, 320)]):
            paths, report = self.build(points=points)
            self.assertNotIn('durationSeconds', paths[6])
            self.assertEqual(1, report['unknownDurationCount'])

    def test_zero_base_price_is_known(self):
        paths, report = self.build(paths=[path(cost=0)])
        self.assertEqual(0, paths[6]['basePriceCopper'])
        self.assertEqual(0, report['unknownPriceCount'])

    def test_invalid_geometry_prices_and_duplicate_ids_fail(self):
        for paths, points in (([path(cost=-1)], None), ([path(), path()], None),
                              (None, [point(0, 0), point(0, 320)]),
                              (None, [point(0, 0), point(1, 'nan')])):
            with self.assertRaises(ValueError):
                self.build(paths=paths, points=points)

    def test_manual_correction_addition_and_disabling(self):
        manual = {'nodes': {'2': {'outgoing': [
            {'id': 6, 'toNodeID': 4, 'durationSeconds': 70, 'source': 'Stopwatch', 'verifiedBuild': '1.60.1.70205'},
            {'toNodeID': 5, 'source': 'Flight master offered', 'verifiedBuild': '1.60.1.70205'},
        ]}}}
        paths, report = self.build(manual=manual)
        self.assertEqual('manual', paths[6]['durationSource'])
        self.assertEqual(70, paths[6]['durationSeconds'])
        self.assertNotIn('basePriceCopper', paths['manual:2:5'])
        self.assertEqual(1, report['unknownPriceCount'])
        manual['nodes']['2']['outgoing'] = [{'id': 6, 'toNodeID': 4, 'disabled': True}]
        self.assertEqual({}, self.build(manual=manual)[0])

    def test_manual_source_and_endpoints_are_validated(self):
        for record in ({'id': 6, 'toNodeID': 4, 'durationSeconds': 1},
                       {'id': 6, 'toNodeID': 5, 'disabled': True},
                       {'toNodeID': 99, 'source': 'test', 'verifiedBuild': '1.60.1.70205'}):
            with self.assertRaises(ValueError):
                self.build(manual={'nodes': {'2': {'outgoing': [record]}}})

    def test_export_coverage_and_manual_source_preservation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manual_path = root / 'tools/manual/forever.json'
            manual_path.parent.mkdir(parents=True)
            source = '{"schemaVersion":1,"nodes":{}}\n'
            manual_path.write_text(source)
            report = generate_paths(root, {'id': 'forever'}, '1.60.1.70205',
                                    [path()], [point(0, 0), point(1, 320)], {2, 4}, load_manual(root, 'forever'))
            self.assertEqual(source, manual_path.read_text())
            self.assertEqual(1, report['pathCount'])
            self.assertEqual(report, json.loads((root / 'readme/coverage/forever.json').read_text()))
            text = (root / 'Data/forever/TaxiPaths.lua').read_text()
            self.assertIn('lib.Client.dataSet ~= "forever"', text)
            before = profile_content_fingerprint(root, 'forever')
            digest_before = fingerprint('forever', root)
            (root / 'Data/forever/TaxiPaths.lua').write_text(text.replace('basePriceCopper = 5', 'basePriceCopper = 6'))
            self.assertNotEqual(before, profile_content_fingerprint(root, 'forever'))
            self.assertNotEqual(digest_before, fingerprint('forever', root))

    def test_complete_profile_requires_paths_and_locales(self):
        required = required_data_paths(Path('root'), 'forever')
        self.assertIn(Path('root/Data/forever/TaxiPaths.lua'), required)
        self.assertIn(Path('root/Locale/forever/zhTW.lua'), required)
        self.assertEqual(17, len(required))

    def test_failed_profile_preserves_installed_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            installed = root / 'Data/forever/TaxiNodes.lua'
            installed.parent.mkdir(parents=True)
            installed.write_text('existing complete snapshot')
            def fail(output, *args):
                generated = output / 'Data/forever/TaxiNodes.lua'
                generated.parent.mkdir(parents=True)
                generated.write_text('incomplete new snapshot')
                raise ValueError('failed path validation')
            with patch('tools.generate._generate_profile', side_effect=fail):
                with self.assertRaises(ValueError):
                    generate_profile(root, {'id': 'forever'}, '1.60.1.70205', None, None)
            self.assertEqual('existing complete snapshot', installed.read_text())

    def test_failed_profile_copy_rolls_back_all_touched_files(self):
        import shutil
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / 'Data/forever'
            folder.mkdir(parents=True)
            for name in ('TaxiNodes.lua', 'TaxiPaths.lua'):
                (folder / name).write_text('old ' + name)
            def generate(output, *args):
                generated = output / 'Data/forever'
                generated.mkdir(parents=True)
                for name in ('TaxiNodes.lua', 'TaxiPaths.lua'):
                    (generated / name).write_text('new ' + name)
            copy = shutil.copyfile
            calls = []
            def fail_second(*args):
                calls.append(args)
                if len(calls) == 2:
                    raise OSError('simulated disk failure')
                return copy(*args)
            with patch('tools.generate._generate_profile', side_effect=generate), patch('tools.generate.shutil.copyfile', side_effect=fail_second):
                with self.assertRaises(OSError):
                    generate_profile(root, {'id': 'forever'}, '1.60.1.70205', None, None)
            for name in ('TaxiNodes.lua', 'TaxiPaths.lua'):
                self.assertEqual('old ' + name, (folder / name).read_text())
            self.assertEqual([], list(folder.glob('*.pending')))

    def test_complete_manual_fallback_accepts_documented_db2_ids(self):
        manual = {'complete': True, 'nodes': {'2': {'outgoing': [
            {'id': 6, 'toNodeID': 4, 'durationSeconds': 70,
             'source': 'Verified flight', 'verifiedBuild': '1.60.1.70205'}]}}}
        paths, report = self.build(paths=[], points=[], manual=manual)
        self.assertEqual('manual', paths[6]['durationSource'])
        self.assertEqual(1, report['unknownPriceCount'])

    def test_same_build_path_corrections_publish(self):
        original = '-- Source: test (build 1.2.3.4)\nprice = 5\n'
        self.assertTrue(is_path_update(original, original.replace('price = 5', 'price = 6')))
        self.assertFalse(is_path_update(original, original.replace('build 1.2.3.4', 'build 1.2.3.5')))
        self.assertTrue(is_path_update(None, original))
        self.assertTrue(is_path_update(original, None))
        self.assertEqual('v2.8.0', plan_release('v2.7.3', path_updates=('forever',)).version.tag())


if __name__ == '__main__':
    unittest.main()
