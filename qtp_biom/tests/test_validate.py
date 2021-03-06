# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The Qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from unittest import main
from tempfile import mkstemp, mkdtemp
from os import close, remove, mkdir
from os.path import exists, isdir, join, basename
from shutil import rmtree
from json import dumps
from functools import partial

import numpy as np
from biom import Table, load_table
from biom.util import biom_open
from qiita_client import ArtifactInfo
from qiita_client.testing import PluginTestCase

from qtp_biom.validate import validate


class CreateTests(PluginTestCase):
    def setUp(self):
        self.out_dir = mkdtemp()
        self._clean_up_files = [self.out_dir]

    def tearDown(self):
        for fp in self._clean_up_files:
            if exists(fp):
                if isdir(fp):
                    rmtree(fp)
                else:
                    remove(fp)

    def _create_job_and_biom(self, sample_ids, template=None, analysis=None):
        # Create the BIOM table that needs to be valdiated
        fd, biom_fp = mkstemp(suffix=".biom")
        close(fd)
        data = np.random.randint(100, size=(2, len(sample_ids)))
        table = Table(data, ['O1', 'O2'], sample_ids)
        with biom_open(biom_fp, 'w') as f:
            table.to_hdf5(f, "Test")
        self._clean_up_files.append(biom_fp)

        # Create a new job
        parameters = {'template': template,
                      'files': dumps({'biom': [biom_fp]}),
                      'artifact_type': 'BIOM',
                      'analysis': analysis}
        data = {'command': dumps(['BIOM type', '2.1.4 - Qiime2', 'Validate']),
                'parameters': dumps(parameters),
                'status': 'running'}
        res = self.qclient.post('/apitest/processing_job/', data=data)
        job_id = res['job']

        return biom_fp, job_id, parameters

    def test_validate_analysis(self):
        sample_ids = ['1.SKM4.640180', '1.SKB8.640193', '1.SKD8.640184',
                      '1.SKM9.640192', '1.SKB7.640196']
        biom_fp, job_id, parameters = self._create_job_and_biom(
            sample_ids, analysis=1)
        obs_success, obs_ainfo, obs_error = validate(
            self.qclient, job_id, parameters, self.out_dir)
        exp_fp = partial(join, self.out_dir)
        exp_index_fp = exp_fp('index.html')
        exp_viz_fp = exp_fp('support_files')
        self.assertTrue(obs_success)
        self.assertEqual(
            obs_ainfo, [ArtifactInfo(None, 'BIOM', [
                (biom_fp, 'biom'), (exp_index_fp, 'html_summary'),
                (exp_viz_fp, 'html_summary_dir')])])
        self.assertEqual(obs_error, "")

    def test_validate_unknown_type(self):
        parameters = {'template': 1, 'files': dumps({'BIOM': ['ignored']}),
                      'artifact_type': 'UNKNOWN'}
        obs_success, obs_ainfo, obs_error = validate(
            self.qclient, 'job-id', parameters, self.out_dir)
        self.assertFalse(obs_success)
        self.assertIsNone(obs_ainfo)
        exp = 'Unknown artifact type UNKNOWN. Supported types: BIOM'
        self.assertEqual(obs_error, exp)

    def test_validate_no_changes(self):
        sample_ids = ['1.SKB2.640194', '1.SKM4.640180', '1.SKB3.640195',
                      '1.SKB6.640176', '1.SKD6.640190', '1.SKM6.640187',
                      '1.SKD9.640182', '1.SKM8.640201', '1.SKM2.640199',
                      '1.SKD2.640178', '1.SKB7.640196', '1.SKD4.640185',
                      '1.SKB8.640193', '1.SKM3.640197', '1.SKD5.640186',
                      '1.SKB1.640202', '1.SKM1.640183', '1.SKD1.640179',
                      '1.SKD3.640198', '1.SKB5.640181', '1.SKB4.640189',
                      '1.SKB9.640200', '1.SKM9.640192', '1.SKD8.640184',
                      '1.SKM5.640177', '1.SKM7.640188', '1.SKD7.640191']
        biom_fp, job_id, parameters = self._create_job_and_biom(
            sample_ids, template=1)

        obs_success, obs_ainfo, obs_error = validate(
            self.qclient, job_id, parameters, self.out_dir)
        exp_fp = partial(join, self.out_dir)
        exp_index_fp = exp_fp('index.html')
        exp_viz_fp = exp_fp('support_files')
        self.assertTrue(obs_success)
        self.assertEqual(
            obs_ainfo, [ArtifactInfo(None, 'BIOM', [
                (biom_fp, 'biom'), (exp_index_fp, 'html_summary'),
                (exp_viz_fp, 'html_summary_dir')])])
        self.assertEqual(obs_error, "")

    def test_validate_no_changes_superset(self):
        sample_ids = ['1.SKB2.640194', '1.SKM4.640180', '1.SKB3.640195',
                      '1.SKB6.640176', '1.SKD6.640190', '1.SKM6.640187',
                      '1.SKD9.640182', '1.SKM8.640201', '1.SKM2.640199']
        biom_fp, job_id, parameters = self._create_job_and_biom(
            sample_ids, template=1)
        obs_success, obs_ainfo, obs_error = validate(
            self.qclient, job_id, parameters, self.out_dir)
        exp_fp = partial(join, self.out_dir)
        exp_index_fp = exp_fp('index.html')
        exp_viz_fp = exp_fp('support_files')

        self.assertTrue(obs_success)
        self.assertEqual(
            obs_ainfo, [ArtifactInfo(None, 'BIOM', [
                (biom_fp, 'biom'), (exp_index_fp, 'html_summary'),
                (exp_viz_fp, 'html_summary_dir')])])
        self.assertEqual(obs_error, "")

    def test_validate_unknown_samples(self):
        prep_info = {
            'SKB8.640193': {'col': 'val1'},
            'SKD8.640184': {'col': 'val2'}}
        data = {'prep_info': dumps(prep_info),
                'study': 1,
                'data_type': '16S'}
        res = self.qclient.post('/apitest/prep_template/', data=data)

        sample_ids = ['Sample1', 'Sample2', 'Sample3']
        biom_fp, job_id, parameters = self._create_job_and_biom(
            sample_ids, template=res['prep'])

        obs_success, obs_ainfo, obs_error = validate(
            self.qclient, job_id, parameters, self.out_dir)
        self.assertFalse(obs_success)
        self.assertIsNone(obs_ainfo)
        exp = ('The sample ids in the BIOM table do not match the ones in the '
               'prep information. Please, provide the column "run_prefix" in '
               'the prep information to map the existing sample ids to the '
               'prep information sample ids.')
        self.assertEqual(obs_error, exp)

    def test_validate_missing_samples(self):
        prep_info = {
            'SKB8.640193': {'col': 'val1',
                            'run_prefix': 'Sample1'},
            'SKD8.640184': {'col': 'val2',
                            'run_prefix': 'Sample2'}}
        data = {'prep_info': dumps(prep_info),
                'study': 1,
                'data_type': '16S'}
        res = self.qclient.post('/apitest/prep_template/', data=data)

        sample_ids = ['Sample1', 'Sample2', 'New.Sample']
        biom_fp, job_id, parameters = self._create_job_and_biom(
            sample_ids, template=res['prep'])

        obs_success, obs_ainfo, obs_error = validate(
            self.qclient, job_id, parameters, self.out_dir)
        self.assertFalse(obs_success)
        self.assertIsNone(obs_ainfo)
        exp = ('Your prep information is missing samples that are present in '
               'your BIOM table: New.Sample')
        self.assertEqual(obs_error, exp)

    def test_validate_run_prefix(self):
        prep_info = {
            'SKB8.640193': {'col': 'val1',
                            'run_prefix': 'Sample1'},
            'SKD8.640184': {'col': 'val2',
                            'run_prefix': 'Sample2'}}
        data = {'prep_info': dumps(prep_info),
                'study': 1,
                'data_type': '16S'}
        res = self.qclient.post('/apitest/prep_template/', data=data)

        sample_ids = ['Sample1', 'Sample2']
        biom_fp, job_id, parameters = self._create_job_and_biom(
            sample_ids, template=res['prep'])
        obs_success, obs_ainfo, obs_error = validate(
            self.qclient, job_id, parameters, self.out_dir)
        exp_fp = partial(join, self.out_dir)
        exp_biom_fp = exp_fp(basename(biom_fp))
        exp_index_fp = exp_fp('index.html')
        exp_viz_fp = exp_fp('support_files')
        self._clean_up_files.append(exp_biom_fp)
        self.assertTrue(obs_success)
        self.assertEqual(
            obs_ainfo, [ArtifactInfo(None, 'BIOM', [
                (exp_biom_fp, 'biom'), (exp_index_fp, 'html_summary'),
                (exp_viz_fp, 'html_summary_dir')])])
        self.assertEqual(obs_error, "")
        obs_t = load_table(exp_biom_fp)
        self.assertCountEqual(obs_t.ids(), ["1.SKB8.640193", "1.SKD8.640184"])

    def test_validate_prefix(self):
        prep_info = {
            'SKB8.640193': {'col': 'val1'},
            'SKD8.640184': {'col': 'val2'}}
        data = {'prep_info': dumps(prep_info),
                'study': 1,
                'data_type': '16S'}
        res = self.qclient.post('/apitest/prep_template/', data=data)

        sample_ids = ['SKB8.640193', 'SKD8.640184']
        biom_fp, job_id, parameters = self._create_job_and_biom(
            sample_ids, template=res['prep'])

        obs_success, obs_ainfo, obs_error = validate(
            self.qclient, job_id, parameters, self.out_dir)
        exp_fp = partial(join, self.out_dir)
        exp_biom_fp = exp_fp(basename(biom_fp))
        exp_index_fp = exp_fp('index.html')
        exp_viz_fp = exp_fp('support_files')

        self._clean_up_files.append(exp_biom_fp)
        self.assertTrue(obs_success)
        self.assertEqual(
            obs_ainfo, [ArtifactInfo(None, 'BIOM', [
                (exp_biom_fp, 'biom'), (exp_index_fp, 'html_summary'),
                (exp_viz_fp, 'html_summary_dir')])])
        self.assertEqual(obs_error, "")
        obs_t = load_table(exp_biom_fp)
        self.assertCountEqual(obs_t.ids(), ['1.SKB8.640193', '1.SKD8.640184'])

    def test_validate_representative_set(self):
        sample_ids = ['1.SKB2.640194', '1.SKM4.640180', '1.SKB3.640195',
                      '1.SKB6.640176', '1.SKD6.640190', '1.SKM6.640187',
                      '1.SKD9.640182', '1.SKM8.640201', '1.SKM2.640199']
        biom_fp, job_id, parameters = self._create_job_and_biom(
            sample_ids, template=1)

        fd, fasta_fp = mkstemp(suffix=".fna")
        close(fd)
        with open(fasta_fp, 'w') as f:
            f.write(">O1 something\nACTG\n>O2\nATGC\n")
        self._clean_up_files.append(fasta_fp)
        exp_fp = partial(join, self.out_dir)
        exp_index_fp = exp_fp('index.html')
        exp_viz_fp = exp_fp('support_files')
        with open(exp_index_fp, 'w') as f:
            f.write("my html")
        mkdir(exp_viz_fp)

        parameters = {'template': parameters['template'],
                      'files': dumps({'biom': [biom_fp],
                                      'preprocessed_fasta': [fasta_fp]}),
                      'artifact_type': 'BIOM'}

        obs_success, obs_ainfo, obs_error = validate(
            self.qclient, job_id, parameters, self.out_dir)
        self.assertTrue(obs_success)
        files = [(biom_fp, 'biom'), (fasta_fp, 'preprocessed_fasta'),
                 (exp_index_fp, 'html_summary'),
                 (exp_viz_fp, 'html_summary_dir')]
        self.assertEqual(
            obs_ainfo, [ArtifactInfo(None, 'BIOM',  files)])
        self.assertEqual(obs_error, "")

        # Extra ids
        with open(fasta_fp, 'w') as f:
            f.write(">O1 something\nACTG\n>O2\nATGC\n>O3\nATGC\n")
        obs_success, obs_ainfo, obs_error = validate(
            self.qclient, job_id, parameters, self.out_dir)
        self.assertFalse(obs_success)
        self.assertIsNone(obs_ainfo)
        self.assertEqual(
            obs_error,
            "The representative set sequence file includes observations not "
            "found in the BIOM table: O3")

        # Missing ids
        with open(fasta_fp, 'w') as f:
            f.write(">O1 something\nACTG\n")
        obs_success, obs_ainfo, obs_error = validate(
            self.qclient, job_id, parameters, self.out_dir)
        self.assertFalse(obs_success)
        self.assertIsNone(obs_ainfo)
        self.assertEqual(
            obs_error,
            "The representative set sequence file is missing observation ids "
            "found in the BIOM tabe: O2")


if __name__ == '__main__':
    main()
