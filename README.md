stormdb
=======

Python classes for interacting with the STORM database at CFIN.

__NB! Help with documentation and examples needed!__

Submodule: access
-----------------

Home of the `Query`-object, used to send queries to the database (_e.g._, for the purpose of getting a list of included subjects).

```
from stormdb.access import Query
q = Query('MINDLAB20XX_MEG-YourProject')
subjects = q.get_subjects()
for sub in subjects:
  # do some work
```

Submodule: process
-----------------

Currently houses the `Maxfilter`-object, which can be used to prepare maxfiltering runs and finally to submit them to the cluster for processing.

```
from stormdb.process import Maxfilter
mf = Maxfilter('MINDLAB20XX_MEG-YourProject')
mf.build_maxfilter_cmd(in_fname, out_fname)
mf.submit_to_isis(n_jobs=4)
# See helps for both methods for more details
```
