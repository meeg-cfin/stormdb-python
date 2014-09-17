# -*- coding: utf-8 -*-
"""
Fill in the dictionary for initial maxfiltering:
- tsss_mc
- autobad on
- estimate origin (y<70mm)

@author: cjb
"""

from access import Query

from mne.preprocessing.maxfilter import fit_sphere_to_headshape
from mne.io import Raw

from maxfilter_cfin import build_maxfilter_cmd, fit_sphere_to_headshape

#from sys import exit as sysexit
import os
import errno
import multiprocessing
import subprocess

def check_path_exists(chkpath):
    
    try: 
        os.makedirs(chkpath)        
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(chkpath):
            pass
        else:
            raise

def _parallel_task(command):
    """
    General purpose method to submit Unix executable-based analyses (e.g.
    maxfilter and freesurfer) to the shell.

    Parameters:
    command:    The command to execute (single string)

    Returns:        The return code (shell) of the command
    """
    #proc = subprocess.Popen([fs_cmd],stdout=subprocess.PIPE, shell=True)
    proc = subprocess.Popen([command], shell=True)

    proc.communicate()
    return proc.returncode

proj_code = 'MINDLAB2013_03-MEG-BlindPerception'
proj_path = '/projects/' + proj_code
analysis_name = 'sss'

VERBOSE=True
FAKE=False # NB
n_processes=3 # Remember that each process is using n_threads cores by default!
n_threads=2 # 2 threads per process

db = Query(proj_code=proj_code,verbose=True)

## Make copies of the binary, calibration and cross-talk correction files
## Place them e.g. in "proj_path"/misc/maxfilter

# cp /neuro/bin/util/x86_64-pc-linux-gnu/maxfilter-2.2.15 .
mx_cmd = proj_path + '/misc/maxfilter/maxfilter-2.2.15'
# cp /neuro/databases/sss/sss_cal.dat .
cal_db = proj_path + '/misc/maxfilter/sss_cal.dat'
# cp /neuro/databases/ctc/ct_sparse.fif .
ctc_db = proj_path + '/misc/maxfilter/ct_sparse.fif'

mf_params_defaults = {'input_file': None, 'output_file': None,
             'autobad': 'on', 'st': False, 'movecomp': False,
             'st_corr': 0.90, 'st_buflen': 10, 'mv_hp': False,
             'origin_head': [0,0,40], 'radius_head': None,
             'bad': None, 'hpicons': True, 'linefreq': 50.,
             'cal': cal_db, 'ctc': ctc_db, 'n_threads': n_threads,
             'force': True, 'verbose': True, 'maxfilter_bin': mx_cmd,
             'logfile': None}

mf_fname_suffix = '_sss'

included_subjects = db.get_subjects()# [0:1]
if not FAKE:
    pool = multiprocessing.Pool(processes=n_processes)


all_cmds = []
for subj in included_subjects:
    output_folder_base = proj_path + '/scratch/maxfilter/' + analysis_name + '/' + subj
    check_path_exists(output_folder_base)
    for study in db.get_studies(subj, modality='MEG', unique=False):
        # make a neuromag-style folder structure!
        output_folder = output_folder_base + '/' + study[2:8]
        check_path_exists(output_folder)

        radius_head = None # only once per study!
        for (session, sesnum) in db.get_series(subj, study, modality='MEG'):
            # Start with a fresh copy of the defaults
            mfp = mf_params_defaults.copy()
            session_output_files = []
            session_mfp = [] #NB: this is a list!!

            session_input_files = db.get_files(subj, study, modality='MEG', series=sesnum)
            for ii_raw, raw_fname in enumerate(sorted(session_input_files)):

                fnum_raw = "%02d" % ii_raw
                mfp['input_file'] = raw_fname
                
                if len(session_input_files) > 1:
                    output_name_base = output_folder + '/'+session+ '-' + fnum_raw
                else:
                    output_name_base = output_folder + '/'+session
            
                if not 'empt' in session.lower(): #### TYPO IN ONE SESSION NAME: emptRy!!
                    # change this to test existence of initial HPI measurement...
                    mfp['output_file'] = output_name_base + mf_fname_suffix + '.fif'
                    mfp['mv_hp'] = output_name_base + mf_fname_suffix + '.pos'
                    mfp['logfile'] = output_name_base + mf_fname_suffix + '.log'
                    if radius_head is None: # only needed once per study (same HPI digs)
                        raw = Raw(raw_fname)
                        radius_head, origin_head, origin_devive = fit_sphere_to_headshape(raw.info,verbose=VERBOSE)
                        raw.close()        
                    mfp['origin_head'] = origin_head
                    mfp['radius_head'] = radius_head

                else:
                    mfp['output_file'] = output_name_base + mf_fname_suffix +'.fif'
                    mfp['mv_hp'] = None
                    mfp['logfile'] = output_name_base + mf_fname_suffix + '.log'
                    mfp['movecomp'] = False
                    mfp['hpicons'] = False
                    mfp['origin_head'] = False # Must be False, if None, will try to estimate it!
                    mfp['radius_head'] = False
            
                # Since both session_input and session_output_files are lists, they
                # will now remain ordered 1-to-1
                session_output_files.append(mfp['output_file'])
                session_mfp.append(mfp.copy())
            
                if not os.path.isfile(mfp['input_file']):
                    #logger.error("Following input file does not exist!")
                    #logger.error(mfp['input_file'])
                    raise Exception("input_file_missing")

                if (os.path.isfile(mfp['output_file']) and not mfp['force']):
                    #if force is None:
                        #logger.error("Output file exists, but option: force is False")
                        #logger.error(mfp['output_file'])
                        #logger.error("Set force-argument to override...")
                    raise Exception("output_file_exists")
                    #elif force is True:
                    #    mfp['force'] = True

                # NB! This would not work if any one of the parameters in mfp were not defined !
                # Meaning: this is a very hard-coded way to define a "generic" maxfilter run...
                mf_cmd = build_maxfilter_cmd(mfp['input_file'], mfp['output_file'], origin=mfp['origin_head'], frame='head',
                                             bad=mfp['bad'], autobad=mfp['autobad'], force=mfp['force'],
                                             st=mfp['st'], st_buflen=mfp['st_buflen'], st_corr=mfp['st_corr'], 
                                             movecomp=mfp['movecomp'], mv_hp=mfp['mv_hp'], hpicons=mfp['hpicons'],
                                             linefreq=mfp['linefreq'], cal=mfp['cal'], ctc=mfp['ctc'], n_threads=mfp['n_threads'],
                                             verbose=mfp['verbose'], maxfilter_bin=mfp['maxfilter_bin'],
                                             logfile=mfp['logfile'])

                #print('Initiating Maxfilter with following command')
                #print(mf_cmd)
                all_cmds.append(mf_cmd)


if not FAKE:
    return_codes = pool.map(_parallel_task,all_cmds)
    pool.close()
    pool.join()

    if any(return_codes):
        print "Some subprocesses didn't complete!"
        print "Return codes: ", return_codes
        print "Dying here, temp files not deleted, see below:"
        print '\n'.join(all_cmds)
        raise
    else:
        print('All subprocesses completed')

elif VERBOSE:
    print "The following would execute, if this were not a FAKE run:"
    for cmd in all_cmds:
        print "%s" % cmd
    # cleanup

