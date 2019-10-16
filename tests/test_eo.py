import json
import os
import unittest

from pystac import *
from pystac.eo import (Band, EOAsset, EOItem, band_desc, band_range, eo_key)
from tests.utils import (TestCases, test_to_from_dict)


class EOItemTest(unittest.TestCase):
    def setUp(self):
        self.URI_1 = TestCases.get_path(
            'data-files/eo/eo-landsat-example.json')
        self.URI_2 = TestCases.get_path(
            'data-files/eo/eo-landsat-example-INVALID.json')
        self.eoi = EOItem.from_file(self.URI_1)
        with open(self.URI_1) as f:
            self.eo_dict = json.load(f)

    def test_to_from_dict(self):
        test_to_from_dict(self, EOItem, self.eo_dict)

    def test_from_file(self):
        self.assertEqual(len(self.eoi.bands), 11)
        for b in self.eoi.bands:
            self.assertIsInstance(b, Band)
        self.assertEqual(len(self.eoi.links), 3)

        href = "https://odu9mlf7d6.execute-api.us-east-1.amazonaws.com/stage/stac/search?id=LC08_L1TP_107018_20181001_20181001_01_RT"
        self.assertEqual(self.eoi.get_self_href(), href)

        with self.assertRaises(STACError):
            EOItem.from_file(self.URI_2)

    def test_from_item(self):
        i = Item.from_file(self.URI_1)
        with self.assertRaises(AttributeError):
            getattr(i, 'bands')
        self.assertTrue(eo_key('bands') in i.properties.keys())
        eoi = EOItem.from_item(i)
        self.assertIsNotNone(getattr(eoi, 'bands'))
        with self.assertRaises(KeyError):
            eoi.properties[eo_key('bands')]

    def test_clone(self):
        eoi_clone = self.eoi.clone()
        compare_eo_items(self, self.eoi, eoi_clone)

    def test_get_assets(self):
        a = self.eoi.get_assets()
        for _, asset in a.items():
            self.assertIsInstance(asset, Asset)
        eoa = self.eoi.get_eo_assets()
        for _, eo_asset in eoa.items():
            self.assertIsInstance(eo_asset, EOAsset)
        self.assertNotEqual(len(a.items()), len(eoa.items()))
        for k in eoa.keys():
            self.assertIn(k, a.keys())

    def test_add_asset(self):
        eoi_c = deepcopy(self.eoi)
        a = Asset('/asset_dir/asset.json')
        eoa = EOAsset('/asset_dir/eo_asset.json', bands=[0, 1])
        for asset in (a, eoa):
            self.assertIsNone(asset.item)
        eoi_c.add_asset('new_asset', a)
        eoi_c.add_asset('new_eo_asset', eoa)
        self.assertEqual(len(eoi_c.assets.items()),
                         len(self.eoi.assets.items()) + 2)
        self.assertEqual(a, eoi_c.assets['new_asset'])
        self.assertEqual(eoa, eoi_c.assets['new_eo_asset'])
        for asset in (a, eoa):
            self.assertEqual(asset.item, eoi_c)

    def test_add_eo_fields_to_dict(self):
        d = {}
        self.eoi.add_eo_fields_to_dict(d)
        comp_d = {k: v for k, v in deepcopy(
            self.eo_dict['properties']).items() if k.startswith('eo:')}
        self.assertDictEqual(d, comp_d)


class EOAssetTest(unittest.TestCase):
    def test_eo_asset(self):
        pass


class BandTest(unittest.TestCase):
    def test_band(self):
        pass


class EOUtilsTest(unittest.TestCase):
    def test_band_desc(self):
        desc = 'Common name: nir, Range: 0.75 to 1.0'
        self.assertEqual(band_desc('nir'), desc)
        self.assertEqual(band_desc('uncommon name'),
                         'Common name: uncommon name')

    def test_band_range(self):
        self.assertEqual(band_range('pan'), (0.50, 0.70))
        self.assertEqual(band_range('uncommon name'), 'uncommon name')

    def test_eo_key(self):
        self.assertEqual(eo_key(''), 'eo:')
        self.assertEqual(eo_key('dsg'), 'eo:dsg')


def compare_eo_items(test_class, eoi_1, eoi_2):
    for eoi in (eoi_1, eoi_2):
        test_class.assertIsInstance(eoi, EOItem)
    test_class.assertEqual(dir(eoi_1), dir(eoi_2))
    test_class.assertEqual(eoi_1.id, eoi_2.id)
    test_class.assertListEqual(eoi_1.bbox, eoi_2.bbox)
    test_class.assertListEqual(eoi_1.stac_extensions, eoi_2.stac_extensions)
    for eoi in (eoi_1, eoi_2):
        eoi.links.sort(key=lambda x: x.target)
    for i in range(len(eoi_1.links)):
        test_class.assertDictEqual(
            eoi_1.links[i].to_dict(), eoi_2.links[i].to_dict())

    for d in ('geometry', 'properties'):
        test_class.assertDictEqual(getattr(eoi_1, d), getattr(eoi_2, d))

    test_class.assertEqual(len(eoi_1.assets.keys()), len(eoi_2.assets.keys()))
    for key in eoi_1.assets.keys():
        if isinstance(eoi_1.assets[key], EOAsset):
            compare_eo_assets(test_class, eoi_1.assets[key], eoi_2.assets[key])
        else:
            test_class.assertDictEqual(
                eoi_1.assets[key].to_dict(), eoi_2.assets[key].to_dict())

    for eof in EOItem.EO_FIELDS:
        if eof == 'bands':
            test_class.assertEqual(len(eoi_1.bands), len(eoi_2.bands))
            for eoi in (eoi_1, eoi_2):
                eoi.bands.sort(key=lambda x: x.name)
            for i in range(len(eoi_1.bands)):
                compare_bands(test_class, eoi_1.bands[i], eoi_2.bands[i])
        else:
            test_class.assertEqual(getattr(eoi_1, eof), getattr(eoi_2, eof))


def compare_eo_assets(test_class, eoa_1, eoa_2):
    for eoa in (eoa_1, eoa_2):
        test_class.assertIsInstance(eoa, EOAsset)
    test_class.assertEqual(eoa_1.href, eoa_2.href)
    test_class.assertListEqual(eoa_1.bands, eoa_2.bands)
    test_class.assertEqual(eoa_1.title, eoa_2.title)
    test_class.assertEqual(eoa_1.media_type, eoa_2.media_type)
    if eoa_1.properties:
        test_class.assertDictEqual(eoa_1.properties, eoa_2.properties)
    else:
        test_class.assertIsNone(eoa_2.properties)


def compare_bands(test_class, b1, b2):
    test_class.assertDictEqual(b1.to_dict(), b2.to_dict())
