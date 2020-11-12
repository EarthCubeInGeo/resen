
.. :changelog:

2020.2.1 (2020-11-12)
+++++++++++++++++++++

- Fixed #73, a bug affecting the update command
- Added documentation for the update command

2020.2.0 (2020-11-06)
+++++++++++++++++++++

- Changed valid core list to be read from JSON file downloaded from resen-core repo rather than hardcoded in source code
- Fixed #63, bug which caused odd behavior with progress bar when downloading cores in narrow terminal window
- Read version number from init file
- Improve documentation on mounting, bucket exporting, and Linux post-installation steps
- Fixed #14, an issue with the resen lockfile

2020.1.0 (2020-06-24)
+++++++++++++++++++++

- Add new available resen-core: 2020.1.0
- Bug fixed when importing a bucket: now tar files of mounted paths are removed after a successful import.
- Fixed bug causing enabling sudo access for user jovyan failed

2019.1.1 (2019-12-10)
+++++++++++++++++++++

- Raise exceptions added when local storage not found
- Add detection of resen running on a windows system
- If docker toolbox, change path to be the docker VM path instead of the host machine path
- Find a port that is available

2019.1.0 (2019-11-24)
+++++++++++++++++++++

- Initial release.
