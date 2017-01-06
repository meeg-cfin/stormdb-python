from stormdb.access import Query, DBError
from nose.tools import assert_true, assert_equal, assert_raises


proj_name = 'MEG_EEG-Training'
bad_proj_name = 'Nonexistent-project_name'
test_subject_name = '0002_M55'
study_modalities = ('MR', 'MEG', 'MEG', 'MR')
study_name_tuple = (3, '20141114_092930')
series_name = 't1_mpr_sag_weakFS'
series_number = 5


def test_proj_name():
    assert_raises(DBError, Query, bad_proj_name)


def test_get_subjects():
    subs = Query(proj_name).get_subjects()
    assert_true(isinstance(subs, list))
    assert_equal(subs[0], test_subject_name)  # 0001 is excluded in DB!


def test_get_studies():
    studies = Query(proj_name).get_studies(test_subject_name)
    assert_equal(len(studies), len(study_modalities))
    assert_equal(studies[study_name_tuple[0]], study_name_tuple[1])


def test_filter_series():
    series = Query(proj_name).filter_series(series_name,
                                            subjects=test_subject_name)
    assert_equal(len(series), 1)
    assert_equal(int(series[0]['serieno']), series_number)
