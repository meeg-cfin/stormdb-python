"""
=========================
Methods to process data in StormDB layout

Credits:
    Several functions are modified versions from those in mne-python
    https://github.com/mne-tools/mne-python
=========================

"""
# Author: Chris Bailey <cjb@cfin.au.dk>
#
# License: BSD (3-clause)
import os
import sys
import logging
import warnings
import numpy as np
import subprocess as subp

from mne.io import Raw
from mne.bem import fit_sphere_to_headshape

from .access import DBError


class Maxfilter():
    """ Object for maxfiltering data from database into StormDB filesystem

    Parameters
    ----------
    proj_code : str
        The name of the project.
    bad : list
        List of a priori bad channels (default: empty list)
    verbose : bool
        If True (default), print out a bunch of information as we go.

    Attributes
    ----------
    proj_code : str
        Name of project
    cmd : list of str
        If defined, represents a sequence of maxfilter shell calls.
    """

    def __init__(self, proj_code, bad=[], verbose=True):
        if not os.path.exists('/projects/' + proj_code):
            raise DBError('No such project!')

        self.proj_code = proj_code
        self.bad = bad
        self.cmd = []
        # Consider placing other vars here

        self.logger = logging.getLogger('__name__')
        self.logger.propagate = False
        stdout_stream = logging.StreamHandler(sys.stdout)
        self.logger.addHandler(stdout_stream)
        if verbose:
            self.logger.setLevel(logging.INFO)
        else:
            self.logger.setLevel(logging.ERROR)

    def detect_bad_chans_xscan(self, in_fname, use_tsss=False, n_jobs=1,
                               xscan_bin=None, set_bad=True):
        """Experimental method from Elekta for detecting bad channels

        Parameters
        ----------
        in_fname : str
            Input file name
        use_tsss : bool
            If True, uses tSSS-based bad channel estimation (slow!). Default
            is False: use tSSS for particularly bad artefacts like dentals.
        xscan_bin : str
            Full path to xscan-binary (if None, default in /neuro/bin is used)
        set_bad : bool
            Set the channels found by xscan as bad in the Maxfilter object
            (default: True). NB: bad-list is amended, not replaced!
        """
        _check_n_jobs(n_jobs)

        if xscan_bin is None:
            xscan_bin = '/neuro/bin/util/xscan'

        # Start building command
        cmd = [xscan_bin, ' -f {:s} -v '.format(in_fname)]

        proc = subp.Popen(cmd, shell=True, stdout=subp.PIPE, stderr=subp.PIPE)
        stdout, stderr = proc.communicate()
        retcode = proc.wait()

        if retcode != 0:
            if retcode >> 8 == 127:
                raise NameError('xscan binary ' + xscan_bin + ' not found')
            else:
                errmsg = 'xscan exited with an error, output is:\n\n' + stderr
                raise RuntimeError(errmsg)

        bads_str = stdout[-1]  # last row is what we want
        self.logger.info('xscan detected the following bad channels:\n' +
                         bads_str)
        if set_bad:
            new_bads = bads_str.split()
            uniq_bads = [b for b in new_bads if b not in self.bad]
            self.bad = uniq_bads
            self.logger.info('Maxfilter object bad channel list updated')

    def build_maxfilter_cmd(self, in_fname, out_fname, origin='0 0 40',
                            frame='head', bad=None, autobad='off', skip=None,
                            force=False, st=False, st_buflen=16.0,
                            st_corr=0.96, mv_trans=None, movecomp=False,
                            mv_headpos=False, mv_hp=None, mv_hpistep=None,
                            mv_hpisubt=None, hpicons=True, linefreq=None,
                            cal=None, ctc=None, mx_args='',
                            maxfilter_bin='/neuro/bin/util/maxfilter',
                            logfile=None):

        """Build a NeuroMag MaxFilter command for later execution.

        See the Maxfilter manual for details on the different options!

        Things to implement
        * check that cal-file matches date in infile!
        * check that maxfilter binary is OK

        Parameters
        ----------
        in_fname : str
            Input file name
        out_fname : str
            Output file name
        maxfilter_bin : str
            Full path to the maxfilter-executable
        logfile : str
            Full path to the output logfile
        origin : array-like or str
            Head origin in mm. If None it will be estimated from headshape
            points.
        frame : str ('device' or 'head')
            Coordinate frame for head center
        bad : str, list (or None)
            List of static bad channels. Can be a list with channel names, or a
            string with channels (with or without the preceding 'MEG')
        autobad : string ('on', 'off', 'n')
            Sets automated bad channel detection on or off
        skip : string or a list of float-tuples (or None)
            Skips raw data sequences, time intervals pairs in sec,
            e.g.: 0 30 120 150
        force : bool
            Ignore program warnings
        st : bool
            Apply the time-domain SSS extension (tSSS)
        st_buflen : float
            tSSS buffer length in sec (disabled if st is False)
        st_corr : float
            tSSS subspace correlation limit (disabled if st is False)
        movecomp : bool (or 'inter')
            Estimates and compensates head movements in continuous raw data.
        mv_trans : str(filename or 'default') (or None)
            Transforms the data into the coil definitions of in_fname,
            or into the default frame. If None, and movecomp is True,
            data will be movement compensated to initial head position.
        mv_headpos : bool
            Estimates and stores head position parameters, but does not
            compensate movements (disabled if movecomp is False)
        mv_hp : string (or None)
            Stores head position data in an ascii file
            (disabled if movecomp is False)
        mv_hpistep : float (or None)
            Sets head position update interval in ms (disabled if movecomp
            is False)
        mv_hpisubt : str('amp', 'base', 'off') (or None)
            Subtracts hpi signals: sine amplitudes, amp + baseline, or switch
            off (disabled if movecomp is False)
        hpicons : bool
            Check initial consistency isotrak vs hpifit
            (disabled if movecomp is False)
        linefreq : int (50, 60) (or None)
            Sets the basic line interference frequency (50 or 60 Hz)
            (None: do not use line filter)
        cal : str
            Path to calibration file
        ctc : str
            Path to Cross-talk compensation file
        mx_args : str
            Additional command line arguments to pass to MaxFilter
        """
        # determine the head origin if necessary
        if origin is None:
            self.logger.info('Estimating head origin from headshape points..')
            raw = Raw(in_fname, preload=False)
            with warnings.filterwarnings('error', category=RuntimeWarning):
                r, o_head, o_dev = fit_sphere_to_headshape(raw.info,
                                                           dig_kind='auto',
                                                           units='m')
            raw.close()

            self.logger.info('Fitted sphere: r = {.1f} mm'.format(r))
            self.logger.info('Origin head coordinates: {.1f} {.1f} {.1f} mm'.
                             format(o_head[0], o_head[1], o_head[2]))
            self.logger.info('Origin device coordinates: {.1f} {.1f} {.1f} mm'.
                             format(o_dev[0], o_dev[1], o_dev[2]))

            self.logger.info('[done]')
            if frame == 'head':
                origin = o_head
            elif frame == 'device':
                origin = o_dev
            else:
                RuntimeError('invalid frame for origin')

        # Start building command
        cmd = (maxfilter_bin + ' -f {:s} -o {:s} -v '.format(in_fname,
                                                             out_fname))

        if isinstance(origin, (np.ndarray, list, tuple)):
            origin = '{:.1f} {:.1f} {:.1f}'.format(origin[0],
                                                   origin[1], origin[2])
        elif not isinstance(origin, str):
            raise(ValueError('origin must be list-like or string'))

        cmd += ' -frame {:s} -origin {:s} -v '.format(frame, origin)

        if bad is not None:
            # format the channels
            if isinstance(bad, str):
                bad = bad.split()
            # now assume we have a list of str with channel names
            bad_logic = [ch[3:] if ch.startswith('MEG') else ch for ch in bad]
            bad_str = ' '.join(bad_logic)

            cmd += '-bad {:s} '.format(bad_str)

        cmd += '-autobad {:s} '.format(autobad)

        if skip is not None:
            if isinstance(skip, list):
                skip = ' '.join(['{:.3f} {:.3f}'.format(s[0], s[1])
                                for s in skip])
            cmd += '-skip {:s} '.format(skip)

        if force:
            cmd += '-force '

        if st:
            cmd += '-st '
            cmd += ' {:d} '.format(st_buflen)
            cmd += '-corr {:.4f} '.format(st_corr)

        if mv_trans is not None:
            cmd += '-trans {:s} '.format(mv_trans)

        if movecomp:
            cmd += '-movecomp '
            if movecomp == 'inter':
                cmd += ' inter '

            if mv_headpos:
                cmd += '-headpos '

            if mv_hp is not None:
                cmd += '-hp {:s} '.format(mv_hp)

            if mv_hpisubt is not None:
                cmd += 'hpisubt {:s} '.format(mv_hpisubt)

            if hpicons:
                cmd += '-hpicons '

        if linefreq is not None:
            cmd += '-linefreq {:d} '.format(linefreq)

        if cal is not None:
            cmd += '-cal {:s} '.format(cal)

        if ctc is not None:
            cmd += '-ctc {:s} '.format(ctc)

        cmd += mx_args

        if logfile:
            cmd += ' | tee ' + logfile

        self.cmd += [cmd]

    def submit_to_isis(self, n_jobs=1, fake=False, submit_script=None):
        """ Submit the command built before for processing on the cluster.

        Things to implement
        * check output?

        Parameters
        ----------
        n_jobs : int
            Number of parallel threads to allow (Intel MKL). Max 12!
        fake : bool
            If true, run a fake run, just print the command that will be
            submitted.
        submit_script : str or None
            Full path to script handling submission. If None (default),
            the default script is used:
            /usr/local/common/meeg-cfin/configurations/bin/submit_to_isis

        """
        if len(self.cmd) < 1:
            raise NameError('cmd to submit is not defined yet')

        _check_n_jobs(n_jobs)
        if submit_script is None:
            submit_script = \
                '/usr/local/common/meeg-cfin/configurations/bin/submit_to_isis'

        if os.system(submit_script + ' 2>&1 > /dev/null') >> 8 == 127:
            raise NameError('submit script ' + submit_script + ' not found')

        for cmd in self.cmd:
            self.logger.info('Command to submit:\n{:s}'.format(cmd))

            submit_cmd = ' '.join((submit_script,
                                   '{:d}'.format(n_jobs), cmd))
            if not fake:
                st = os.system(submit_cmd)
                if st != 0:
                    raise RuntimeError('qsub returned non-zero '
                                       'exit status {:d}'.format(st))
            else:
                print('Fake run, nothing executed. The command built is:')
                print(submit_cmd)
                self.logger.info('Nothing executed.')


def _check_n_jobs(n_jobs):
    """Check that n_jobs is sane"""
    if n_jobs > 12:
        raise ValueError('isis only has 12 cores!')
    elif n_jobs < 1 or type(n_jobs) is not int:
        raise ValueError('number of jobs must be a positive integer!')
