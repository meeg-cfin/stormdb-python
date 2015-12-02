"""
=========================
Methods to interact with the STORM database
=========================

"""
# Author: Chris Bailey <cjb@cfin.au.dk>
#
# License: BSD (3-clause)


import subprocess as subp
from getpass import getuser, getpass
import os
import requests
from os.path import join as opj


class DBError(Exception):
    """
    Exception to raise when StormDB returns an error.
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Query():
    """ Query object for communicating with the STORM database

    Parameters
    ----------
    proj_code : str
        The name of the project.
    stormdblogin : str
        The filename to store database login credentials as a hash.
        The default '~/.stormdblogin' should be OK for everyone. If the file
        does not exist (e.g., for first-time users), the user will be
        prompted for a username and password.
    username : str | None
        Define username for login. If None (default), current user is assumed.

    Attributes
    ----------
    proj_code : str
        Name of project
    """

    def __init__(self, proj_code, stormdblogin='~/.stormdblogin',
                 username=None, verbose=None):
        if not os.path.exists('/projects/' + proj_code):
            raise DBError('No such project!')

        self.proj_code = proj_code
        #  self._server = 'http://hyades00.pet.auh.dk/modules/StormDb/extract/'
        self._server = 'http://hyades00.pet.auh.dk/modules/StormDb/extract/'
        self._wget_cmd = 'wget -qO - test ' + self._server

        try:
            with open(os.path.expanduser(stormdblogin), 'r',
                      encoding='utf-8') as fid:
                if verbose:
                    print('Reading login credentials from ' + stormdblogin)
                self._login_code = fid.readline()
        except IOError:
            print('Login credentials not found, please enter them here')
            print('WARNING: This might not work if you\'re in an IDE '
                  '(e.g. spyder)!')
            if username:
                usr = username
            else:
                usr = getuser()

            prompt = 'User \"{:s}\", please enter your password: '.format(usr)
            pwd = getpass(prompt)
            print(pwd)

            url = opj('login/username/', usr, '/password/', pwd)
            #  output = self._wget_system_call(url)
            output = self._send_request(url)
            self._login_code = output

            print("Code generated, writing to {:s}".format(stormdblogin))
            with open(os.path.expanduser(stormdblogin), 'w') as fout:
                fout.write(self._login_code.encode('UTF-8'))
            # Use octal representation
            os.chmod(os.path.expanduser(stormdblogin), 0o400)

    @staticmethod
    def _wget_error_handling(stdout):
        if stdout.find('error') != -1:
            raise DBError(stdout)

        return(0)

    def _wget_system_call(self, url, verbose=False):
        cmd = self._wget_cmd + url

        if verbose:
            print(cmd)

        pipe = subp.Popen(cmd, stdout=subp.PIPE, stderr=subp.PIPE, shell=True)
        output, stderr = pipe.communicate()

        self._wget_error_handling(output.decode(encoding='UTF-8'))

        # Python 3.x treats pipe strings as bytes, which need to be encoded
        # Here assuming shell output is in UTF-8
        return(output.decode(encoding='UTF-8'))

    def _check_response(response):
        if response.find('error') != -1:
            raise DBError(response)

        return(0)

    def _send_request(self, url, verbose=False):
        full_url = self._server + url

        if verbose:
            print(full_url)

        try:
            req = requests.get(full_url)
        except ConnectionError as err:
            print('hyades00 is not responding, it may be down.')
            print('Contact a system administrator for confirmation.')
            raise

        self._check_response(req.content.decode(encoding='UTF-8'))

        # Python 3.x treats pipe strings as bytes, which need to be encoded
        # Here assuming shell output is in UTF-8
        return(req.content.decode(encoding='UTF-8'))

    def get_subjects(self, subj_type='included'):
        """Get list of subjects from database

        Parameters
        ----------
        subj_type : str
            Must be either 'included' or 'excluded'. Returned list is
            determined by database.

        Returns
        -------
        subjects : list of str
            Subject ID codes as returned by the database.
            If no subjects are found, an empty list is returned
        """
        if subj_type == 'included':
            scode = 'subjectswithcode'
        elif subj_type == 'excluded':
            scode = 'excludedsubjectswithcode'
        else:
            raise NameError("""subj_type must be either 'included' or
                            'excluded'""")

        url = opj(scode, '?', self._login_code, '\\&projectCode=',
                  self.proj_code)
        output = self._wget_system_call(url)

        # Split at '\n'
        subj_list = output.split('\n')
        # Remove any empty entries!
        subj_list = [x for x in subj_list if x]

        return(subj_list)

    def get_studies(self, subj_id, modality=None, unique=False):
        """Get list of studies from database for specified subject

        Parameters
        ----------
        subj_id : str
            A string uniquely identifying a subject in the database.
            For example: '0001_ABC'
        modality : str | None
            A string defining the modality of the studies to get. Valid
            examples include 'MEG' and 'MR'. If None, all studies are
            returned regardless of modality.
        unique : bool
            If True, only the chronologically first study of the desired
            modality is returned. Default is False (return all studies
            that match the modality).

        Returns
        -------
        studies : list of str
            Study IDs as returned by the database.
            If no studies are found, an empty list is returned
        """

        url = 'studies?' + self._login_code + \
            '\\&projectCode=' + self.proj_code + '\\&subjectNo=' + subj_id
        output = self._wget_system_call(url)

        # Split at '\n'
        stud_list = output.split('\n')
        # Remove any empty entries!
        stud_list = [x for x in stud_list if x]

        if modality:
            for ii, study in enumerate(stud_list):
                url = 'modalities?' + self._login_code + \
                    '\\&projectCode=' + self.proj_code + '\\&subjectNo=' + \
                      subj_id + '\\&study=' + study
                output = self._wget_system_call(url).split('\n')

                if modality in output:
                    if unique:
                        return([study, ])  # always return a list
                else:
                    stud_list[ii] = None

            # In Py3, filter returns an iterable object, but here we want list
            stud_list = list(filter(None, stud_list))

        return(stud_list)

    def get_series(self, subj_id, study, modality):
        """Get list of series from database for specified subject, study and
        modality.

        Parameters
        ----------
        subj_id : str
            A string uniquely identifying a subject in the database.
            For example: '0001_ABC'
        study : str
            A string uniquely identifying a study in the database for
            given subject.
        modality : str
            A string defining the modality of the study to get.

        Returns
        -------
        series : dict
            A dictionary with keys corresponding to the series names, as
            defined in the database, and values corresponding to the
            index of the series in the study (1-based). If no series are
            found, an empty dict is returned.

        Notes
        -----
        The choice of a dict as output can be reconsidered.
        """
        url = 'series?' + self._login_code + '\\&projectCode=' + \
            self.proj_code + '\\&subjectNo=' + \
            subj_id + '\\&study=' + study + '\\&modality=' + modality
        output = self._wget_system_call(url)

        # Split at '\n'
        series_list = output.split('\n')
        # Remove any empty entries!
        series_list = [x for x in series_list if x]

        # create a 2D list with series name (as string)
        # in 1st column and numerical index (also as string) in 2nd column
        series_list_2d = [x.split(' ') for x in series_list]

        series_dict = {key: value for key, value in series_list_2d}

        return(series_dict)

    def get_files(self, subj_id, study, modality, series):
        """Get list of files from database for specified subject, study,
        modality and series.

        Parameters
        ----------
        subj_id : str
            A string uniquely identifying a subject in the database.
            For example: '0001_ABC'
        study : str
            A string uniquely identifying a study in the database for
            given subject.
        modality : str
            A string defining the modality of the study to get.
        series : str or int
            A string or int defining the index (1-based) of the series to get.

        Returns
        -------
        files : list of str
            List of absolute pathnames to file(s) in series. If no files are
            found, an empty list is returned.
        """
        if type(series) is int:
            series = str(series)

        url = 'files?' + self._login_code + '\\&projectCode=' + \
              self.proj_code + '\\&subjectNo=' + subj_id + '\\&study=' + \
              study + '\\&modality=' + modality + '\\&serieNo=' + series
        output = self._wget_system_call(url)

        # Split at '\n'
        file_list = output.split('\n')
        # Remove any empty entries!
        file_list = [x for x in file_list if x]

        return(file_list)


if __name__ == '__main__':

    project_code = 'MEG_service'

    Q = Query(proj_code=project_code)
    print(Q)
