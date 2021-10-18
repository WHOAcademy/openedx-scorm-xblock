# Adding support to SCORM import export

## Problem Statement
The `openedx-scorm-xblock` package does not provide support to the native import-export functionality of Open edX. Meaning, when we export and import a course containing a SCORM xblock, the uploaded SCORM file was not found and the unit throws a 404 error.

## The idea
The plan was to use another library `abstract-scorm-xblock` that was purposefully created to fix this issue. As we have modified the logics of this repository as per our use case, we did not want to fully migrate to another library.

## The solution that worked
As we are uploading the SCORM file to `Files & Uploads` section under a course, the xblock will contain only the filename instead of the file itself.

So we borrowed the code snippet from the `abstract-scorm-xblock` which runs a search on mongo contentstore for the filename and fetches the file as a byte string. This further will be converted into a `ContentFile` and linked back to the original source code of the `openedx-scorm-xblock` which extracts the zipfile and saves it to default storage.

## Reference Links
- https://abstract-technology.com/lab/articles/working-with-scorm-xblock
- https://github.com/Abstract-Tech/abstract-scorm-xblock
- https://github.com/Abstract-Tech/abstract-scorm-xblock/blob/master/abstract_scorm_xblock/abstract_scorm_xblock/scormxblock.py#L319
- https://github.com/Abstract-Tech/abstract-scorm-xblock/blob/master/abstract_scorm_xblock/abstract_scorm_xblock/scormxblock.py#L343

## Related Pull Requests
- https://github.com/WHOAcademy/openedx-scorm-xblock/pull/3