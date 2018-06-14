import os
import unittest

import mock

from pulp_docker.common import tarutils


busybox_tar_path = os.path.join(os.path.dirname(__file__), '../data/busyboxlight.tar')
skopeo_tar_path = os.path.join(os.path.dirname(__file__), '../data/skopeo.tar')

# these are in correct ancestry order
busybox_ids = (
    '769b9341d937a3dba9e460f664b4f183a6cecdd62b337220a28b3deb50ee0a02',
    '48e5f45168b97799ad0aafb7e2fef9fac57b5f16f6db7f67ba2000eb947637eb',
    'bf747efa0e2fa9f7c691588ce3938944c75607a7bb5e757f7369f86904d97c78',
    '511136ea3c5a64f264b78b5433614aec563103b4d4702f3ba7d4d2698e22c158',
)

# This is a test metadata returned by tarutils.get_metadata when used on busybox.tar.
test_metadata_with_multiple_images_sharing_a_single_parent = {
    u'150ddf0474655d12dcc79b0d5ee360dadcfba01e25d89dee71b4fed3d0c30fbe': {
        'parent': u'faab0acffc50714526b090fa60e0a55d79fc5b34fabbe6b964ca09cbb62f2026',
        'size': 0},
    u'4bf469521ee475733b739c3b15876b8d2b1102e3ce007f48a058e8830c9d2b47': {
        'parent': u'6c991eb934609424f761d3d0a7c79f4f72b76db286aa02e617659ac116aa7758',
        'size': 5454693},
    u'511136ea3c5a64f264b78b5433614aec563103b4d4702f3ba7d4d2698e22c158': {
        'parent': None,
        'size': 0},
    u'6c991eb934609424f761d3d0a7c79f4f72b76db286aa02e617659ac116aa7758': {
        'parent': u'511136ea3c5a64f264b78b5433614aec563103b4d4702f3ba7d4d2698e22c158',
        'size': 0},
    u'89aba41176b8f979bae09db1df5d6f3b58584318fce5d9e56b49c5a3e9700ab4': {
        'parent': u'4bf469521ee475733b739c3b15876b8d2b1102e3ce007f48a058e8830c9d2b47',
        'size': 0},
    u'8e36c99cfab52f0cf6f1aed7674cbdfe57e2ec8d29cdfdfac816b1d659d3ca9e': {
        'parent': u'900ce1b454ef7494e87709c727b8a456167eb7ea7bd202cb0d4b9911a6f05a5e',
        'size': 0},
    u'900ce1b454ef7494e87709c727b8a456167eb7ea7bd202cb0d4b9911a6f05a5e': {
        'parent': u'6c991eb934609424f761d3d0a7c79f4f72b76db286aa02e617659ac116aa7758',
        'size': 2433303},
    u'faab0acffc50714526b090fa60e0a55d79fc5b34fabbe6b964ca09cbb62f2026': {
        'parent': u'6c991eb934609424f761d3d0a7c79f4f72b76db286aa02e617659ac116aa7758',
        'size': 5609404}
}

# This is the image manifest returned by tarutils.get_image_manifest when used on skopeo.tar.
test_image_manifest = {
    u'config': {
        u'digest': u'sha256:efe10ee6727fe52d2db2eb5045518fe98d8e31fdad1cbdd5e1f737018c349ebb',
        u'mediaType': u'application/vnd.docker.container.image.v1+json',
        u'size': 1506},
    u'layers': [{
        u'digest': u'sha256:9e87eff13613eed2f67b0188f8604d1bbdd3a7f5d6a4f565e8923817db65d6e5',
        u'mediaType': u'application/vnd.docker.image.rootfs.diff.tar.gzip',
        u'size': 715112}],
    u'mediaType': u'application/vnd.docker.distribution.manifest.v2+json',
    u'schemaVersion': 2
}


class TestGetMetadata(unittest.TestCase):
    def test_path_does_not_exist(self):
        self.assertRaises(IOError, tarutils.get_metadata, '/a/b/c/d')

    def test_get_from_busybox(self):
        metadata = tarutils.get_metadata(busybox_tar_path)

        self.assertEqual(set(metadata.keys()), set(busybox_ids))
        for i, image_id in enumerate(busybox_ids):
            data = metadata[image_id]
            if i == len(busybox_ids) - 1:
                # make sure the base image has parent set to None
                self.assertTrue(data['parent'] is None)
            else:
                # make sure all other layers have the correct parent
                self.assertEqual(data['parent'], busybox_ids[i + 1])

            # this image does not have a Size attribute in its json
            if image_id.startswith('511136ea'):
                self.assertTrue(data['size'] is None)
            else:
                self.assertTrue(isinstance(data['size'], int))


class TestGetTags(unittest.TestCase):
    def test_normal(self):
        tags = tarutils.get_tags(busybox_tar_path)

        self.assertEqual(tags, {'latest': busybox_ids[0]})

    @mock.patch('json.load', spec_set=True)
    def test_no_repos(self, mock_load):
        mock_load.return_value = {}

        self.assertRaises(ValueError, tarutils.get_tags, busybox_tar_path)


class TestGetAncestry(unittest.TestCase):
    def test_from_busybox(self):
        metadata = tarutils.get_metadata(busybox_tar_path)
        ancestry = tarutils.get_ancestry(busybox_ids[0], metadata)

        self.assertEqual(ancestry, busybox_ids)


class TestGetYoungestChildren(unittest.TestCase):
    def test_with_busybox_light(self):
        metadata = tarutils.get_metadata(busybox_tar_path)
        ret = tarutils.get_youngest_children(metadata)

        self.assertEqual(ret, [busybox_ids[0]])

    def test_with_busybox(self):
        ret = tarutils.get_youngest_children(
            test_metadata_with_multiple_images_sharing_a_single_parent)
        expected_youngest_children = [
            '150ddf0474655d12dcc79b0d5ee360dadcfba01e25d89dee71b4fed3d0c30fbe',
            '89aba41176b8f979bae09db1df5d6f3b58584318fce5d9e56b49c5a3e9700ab4',
            '8e36c99cfab52f0cf6f1aed7674cbdfe57e2ec8d29cdfdfac816b1d659d3ca9e']
        self.assertEqual(set(ret), set(expected_youngest_children))


class TestGetImageManifest(unittest.TestCase):
    def test_with_skopeo(self):
        ret = tarutils.get_image_manifest(skopeo_tar_path)
        self.assertEqual(ret, test_image_manifest)

    def test_with_busybox(self):
        ret = tarutils.get_image_manifest(busybox_tar_path)
        self.assertEqual(ret, [])
