from stormdb.access import Query
from stormdb.process import Maxfilter
from os.path import join
from os import makedirs

proj_name = 'MINDLAB2018_MEG-SF-Integration-Images'
mf_out_path = join('/projects', proj_name, 'scratch', 'maxfiltered')
log_out_path = join('/projects', proj_name, 'scratch', 'maxfiltered', 'logs')
makedirs(log_out_path, exist_ok=True)

qy = Query(proj_name)
mf = Maxfilter(proj_name)

# Get all series (regardless of subject) named '*SFtuned*' (note wildcards)
series = qy.filter_series(description='*SFtuned*')
# Restrict to specific subjects
# series = qy.filter_series(description='*SFtuned*', subjects=['0007', '0012'])
# Restrict to specific modality
# series = qy.filter_series(description='*mprage*', modalities='MR')

for ses in series:
    # MEG acquistions will be split into 2GB chunks if long
    for fifname in ses['files']:
        in_fname = join(ses['path'], fifname)

        outbase = splitext(fifname)[0]
        out_fname = join(mf_out_path, outbase + '_tsss.fif')
        log_fname = join(log_out_path, outbase + '_tsss.log')

        # see maxfilter manual for options
        mf.build_cmd(in_fname, out_fname, logfile=log_fname,
                autobad='on', st=True, st_buflen=16.0, st_corr=0.96,
                force=False)

mf.submit(fake=True)  # remove "fake" when ready to submit!

# mf.commands contains a list of commands that will be sent to cluster
