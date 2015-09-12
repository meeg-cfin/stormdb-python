"""
=========================
Methods to interact with the STORM database
=========================

"""
# Author: Chris Bailey <cjb@cfin.au.dk>
#
# License: BSD (3-clause)


import subprocess as subp
from sys import exit as sysexit
from getpass import getuser, getpass
import os


class Query():
    """
    Query object for communicating with the STORM database
    """

    def __init__(self, proj_code, stormdblogin='~/.stormdblogin', username=None, verbose=None):

        if os.path.exists('/projects/' + proj_code):
            pass
        else:
            print('ERROR: Bad project code?')
            sysexit(-1)

        self.proj_code = proj_code
        self._server = 'http://hyades00.pet.auh.dk/modules/StormDb/extract/'
        self._wget_cmd = 'wget -qO - test ' + self._server

        try:
            with open(os.path.expanduser(stormdblogin)):
                if verbose:
                    print('Reading login credentials from ' + stormdblogin)
                f = open(os.path.expanduser(stormdblogin))
                self._login_code = f.readline()
                f.close()
        except IOError:
            print('Login credentials not found, please enter them here')
            print('WARNING: This might not work if you\'re in an IDE (e.g. spyder)!')
            if username:
                usr = username
            else:
                usr = getuser()

            prompt = 'User \"{:s}\", please enter your password: '.format(usr)
            pwd = getpass(prompt)

            url = 'login/username/' + usr + '/password/' + pwd
            output = self._wget_system_call(url)
            self._login_code = output
            #stormdblogin='~/.stormdbdblogin'
            print("Code generated, writing to {:s}".format(stormdblogin))
            fout = open(os.path.expanduser(stormdblogin), 'w')
            fout.write(self._login_code)
            fout.close()
            os.chmod(os.path.expanduser(stormdblogin), 0400)

    @staticmethod
    def _wget_error_handling(stdout):
        if 'error' in stdout:
            print('Something is wrong, database answers '
                  'as follows (dying...):')
            print(stdout)
            return(-1)

        return(0)

    def _wget_system_call(self, url, verbose=False):
        cmd = self._wget_cmd + url

        if verbose:
            print(cmd)

        pipe = subp.Popen(cmd, stdout=subp.PIPE, stderr=subp.PIPE, shell=True)
        output, stderr = pipe.communicate()
        #output = subp.call([cmd,opts], shell=True)

        if self._wget_error_handling(output) < 0:
            sysexit(-1)

        return(output)

    def get_subjects(self, subj_type='included', verbose=False):

        if subj_type == 'all':  # Doesn't work yet!
            scode = 'subjectswithcode'
        elif subj_type == 'included':
            scode = 'subjectswithcode'
        elif subj_type == 'excluded':
            scode = 'excludedsubjectswithcode'
        else:
            scode = 'subjectswithcode'

        url = scode + '?' + self._login_code + '\\&projectCode=' + self.proj_code
        output = self._wget_system_call(url)

        # Split at '\n'
        subj_list = output.split('\n')
        # Remove any empty entries!
        subj_list = [x for x in subj_list if x]

        if verbose:
            print("Found following subjects:")
            print(subj_list)

        return(subj_list)

    def get_studies(self, subj_id, modality=None, unique=True, verbose=False):

        url = 'studies?' + self._login_code + '\\&projectCode=' + self.proj_code + '\\&subjectNo=' + subj_id
        output = self._wget_system_call(url)

        # Split at '\n'
        stud_list = output.split('\n')
        # Remove any empty entries!
        stud_list = [x for x in stud_list if x]

        if modality:
            for ii,study in enumerate(stud_list):
                url = 'modalities?' + self._login_code + '\\&projectCode=' + self.proj_code + '\\&subjectNo=' + \
                      subj_id + '\\&study=' + study
                output = self._wget_system_call(url).split('\n')
                #print(output, '==', modality)

                if modality in output:
                    if unique:
                        return(study) # NB: returns string! Should change to [study] to return(list...
                else:
                    stud_list[ii] = None

            stud_list = filter(None, stud_list)
#                for entry in output:
#                    if entry == modality:
#                        if unique:
#                            return(study
#                            ### NB!! This only matches first hit! If subject contains several studies
#                            ### with this modality,
#                            ### only first one is returned... Fix me!
#                    else:
#                        stud_list = [x for x in stud_list if x
#                        else:
#                            # must re-write code a bit to accommodate the existence of
#                            # several studies containing the desired modality...
#                            print("Error: non-unique modalities not implemented yet!")
#                            sysexit(-1)

            # If we get this far, no studies found with the desired modality
            if verbose:
                print("No studies found with the desired modality")
                return(None)

        return(stud_list)

    def get_series(self, subj_id, study, modality, verbose=False):

        url = 'series?' + self._login_code + '\\&projectCode=' + self.proj_code + '\\&subjectNo=' + \
              subj_id + '\\&study=' + study + '\\&modality=' + modality
        output = self._wget_system_call(url, verbose=verbose)

        # Split at '\n'
        series_list = output.split('\n')
        # Remove any empty entries!
        series_list = [x for x in series_list if x]

        # return(a 2D list with series number (as string) in 1st column and name as 2nd column
        series_list_2d = [x.split(' ') for x in series_list]

        if verbose:
            print("Found following series:")
            print(series_list_2d)

        return(series_list_2d)

    def get_files(self, subj_id, study, modality, series, verbose=False):
        # NB: Series can be either just the number (1) or number.name (001.VS_1b_1)

        url = 'files?' + self._login_code + '\\&projectCode=' + self.proj_code + \
              '\\&subjectNo=' + subj_id + '\\&study=' + study + '\\&modality=' + \
              modality + '\\&serieNo=' + series
        output = self._wget_system_call(url)

        # Split at '\n'
        file_list = output.split('\n')
        # Remove any empty entries!
        file_list = [x for x in file_list if x]

        if verbose:
            print("Found following files:")
            print(file_list)

        return(file_list)

    def __str__(self):
        print("print(not implemented yet!")


if __name__ == '__main__':

    #test code

    project_code = 'MEG_service'

    Q = Query(proj_code=project_code)
    print(Q)
