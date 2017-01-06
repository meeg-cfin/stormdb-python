from stormdb.access import Query, DBError
from stormdb.cluster import Cluster, ClusterJob, ClusterBatch
from nose.tools import assert_true, assert_equal, assert_raises


proj_name = 'MEG_EEG-Training'
test_subject_name = '0002_M55'
study_modalities = ('MR', 'MEG', 'MEG', 'MR')
study_name_tuple = (3, '20141114_092930')
series_name = 't1_mpr_sag_weakFS'
series_number = 5


def test_job_working_dir():
    # needs work :)
    pass
