# Copyright (c) 2014 VMware, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Unit tests for PBM utility methods.
"""

import os

import mock
import six.moves.urllib.parse as urlparse
import six.moves.urllib.request as urllib

from oslo_vmware import pbm
from oslo_vmware.tests import base


class PBMUtilityTest(base.TestCase):
    """Tests for PBM utility methods."""

    def test_get_all_profiles(self):
        session = mock.Mock()
        session.pbm = mock.Mock()
        profile_ids = mock.Mock()

        def invoke_api_side_effect(module, method, *args, **kwargs):
            self.assertEqual(session.pbm, module)
            self.assertTrue(method in ['PbmQueryProfile',
                                       'PbmRetrieveContent'])
            self.assertEqual(session.pbm.service_content.profileManager,
                             args[0])
            if method == 'PbmQueryProfile':
                self.assertEqual('STORAGE',
                                 kwargs['resourceType'].resourceType)
                return profile_ids
            self.assertEqual(profile_ids, kwargs['profileIds'])

        session.invoke_api.side_effect = invoke_api_side_effect
        pbm.get_all_profiles(session)
        self.assertEqual(2, session.invoke_api.call_count)

    def test_get_all_profiles_with_no_profiles(self):
        session = mock.Mock()
        session.pbm = mock.Mock()
        session.invoke_api.return_value = []
        profiles = pbm.get_all_profiles(session)
        session.invoke_api.assert_called_once_with(
            session.pbm,
            'PbmQueryProfile',
            session.pbm.service_content.profileManager,
            resourceType=session.pbm.client.factory.create())
        self.assertEqual([], profiles)

    def _create_profile(self, profile_id, name):
        profile = mock.Mock()
        profile.profileId = profile_id
        profile.name = name
        return profile

    @mock.patch.object(pbm, 'get_all_profiles')
    def test_get_profile_id_by_name(self, get_all_profiles):
        profiles = [self._create_profile(str(i), 'profile-%d' % i)
                    for i in range(0, 10)]
        get_all_profiles.return_value = profiles

        session = mock.Mock()
        exp_profile_id = '5'
        profile_id = pbm.get_profile_id_by_name(session,
                                                'profile-%s' % exp_profile_id)
        self.assertEqual(exp_profile_id, profile_id)
        get_all_profiles.assert_called_once_with(session)

    @mock.patch.object(pbm, 'get_all_profiles')
    def test_get_profile_id_by_name_with_invalid_profile(self,
                                                         get_all_profiles):
        profiles = [self._create_profile(str(i), 'profile-%d' % i)
                    for i in range(0, 10)]
        get_all_profiles.return_value = profiles

        session = mock.Mock()
        profile_id = pbm.get_profile_id_by_name(session,
                                                ('profile-%s' % 11))
        self.assertFalse(profile_id)
        get_all_profiles.assert_called_once_with(session)

    def test_filter_hubs_by_profile(self):
        pbm_client = mock.Mock()
        session = mock.Mock()
        session.pbm = pbm_client
        hubs = mock.Mock()
        profile_id = 'profile-0'

        pbm.filter_hubs_by_profile(session, hubs, profile_id)
        session.invoke_api.assert_called_once_with(
            pbm_client,
            'PbmQueryMatchingHub',
            pbm_client.service_content.placementSolver,
            hubsToSearch=hubs,
            profile=profile_id)

    def _create_datastore(self, value):
        ds = mock.Mock()
        ds.value = value
        return ds

    def test_convert_datastores_to_hubs(self):
        ds_values = []
        datastores = []
        for i in range(0, 10):
            value = "ds-%d" % i
            ds_values.append(value)
            datastores.append(self._create_datastore(value))

        pbm_client_factory = mock.Mock()
        pbm_client_factory.create.side_effect = lambda *args: mock.Mock()
        hubs = pbm.convert_datastores_to_hubs(pbm_client_factory, datastores)
        self.assertEqual(len(datastores), len(hubs))
        hub_ids = [hub.hubId for hub in hubs]
        self.assertEqual(set(ds_values), set(hub_ids))

    def test_filter_datastores_by_hubs(self):
        ds_values = []
        datastores = []
        for i in range(0, 10):
            value = "ds-%d" % i
            ds_values.append(value)
            datastores.append(self._create_datastore(value))

        hubs = []
        hub_ids = ds_values[0:int(len(ds_values) / 2)]
        for hub_id in hub_ids:
            hub = mock.Mock()
            hub.hubId = hub_id
            hubs.append(hub)

        filtered_ds = pbm.filter_datastores_by_hubs(hubs, datastores)
        self.assertEqual(len(hubs), len(filtered_ds))
        filtered_ds_values = [ds.value for ds in filtered_ds]
        self.assertEqual(set(hub_ids), set(filtered_ds_values))

    def test_get_pbm_wsdl_location(self):
        wsdl = pbm.get_pbm_wsdl_location(None)
        self.assertIsNone(wsdl)

        def expected_wsdl(version):
            driver_abs_dir = os.path.abspath(os.path.dirname(pbm.__file__))
            path = os.path.join(driver_abs_dir, 'wsdl', version,
                                'pbmService.wsdl')
            return urlparse.urljoin('file:', urllib.pathname2url(path))

        with mock.patch('os.path.exists') as path_exists:
            path_exists.return_value = True
            wsdl = pbm.get_pbm_wsdl_location('5')
            self.assertEqual(expected_wsdl('5'), wsdl)
            wsdl = pbm.get_pbm_wsdl_location('5.5')
            self.assertEqual(expected_wsdl('5.5'), wsdl)
            wsdl = pbm.get_pbm_wsdl_location('5.5.1')
            self.assertEqual(expected_wsdl('5.5'), wsdl)
            path_exists.return_value = False
            wsdl = pbm.get_pbm_wsdl_location('5.5')
            self.assertIsNone(wsdl)

    def test_get_profiles(self):
        pbm_service = mock.Mock()
        session = mock.Mock(pbm=pbm_service)

        object_ref = mock.Mock()
        pbm_service.client.factory.create.return_value = object_ref

        profile_id = mock.sentinel.profile_id
        session.invoke_api.return_value = profile_id

        value = 'vm-1'
        vm = mock.Mock(value=value)
        ret = pbm.get_profiles(session, vm)

        self.assertEqual(profile_id, ret)
        session.invoke_api.assert_called_once_with(
            pbm_service,
            'PbmQueryAssociatedProfile',
            pbm_service.service_content.profileManager,
            entity=object_ref)
        self.assertEqual(value, object_ref.key)
        self.assertEqual('virtualMachine', object_ref.objectType)

    def test_get_profiles_by_ids(self):
        pbm_service = mock.Mock()
        session = mock.Mock(pbm=pbm_service)

        profiles = mock.sentinel.profiles
        session.invoke_api.return_value = profiles

        profile_ids = mock.sentinel.profile_ids
        ret = pbm.get_profiles_by_ids(session, profile_ids)

        self.assertEqual(profiles, ret)
        session.invoke_api.assert_called_once_with(
            pbm_service,
            'PbmRetrieveContent',
            pbm_service.service_content.profileManager,
            profileIds=profile_ids)

    def test_get_profiles_by_empty_ids(self):
        session = mock.Mock()
        self.assertEqual([], pbm.get_profiles_by_ids(session, []))
