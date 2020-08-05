import datetime
import logging
from subprocess import Popen

from django.conf import settings

CONFINDR_EXE = settings.CONFINDR_EXE
CONFINDR_DB_SETUP = CONFINDR_EXE.parent / 'confindr_database_setup'
CONFINDR_SECRET = settings.CONFINDR_SECRET
CONFINDR_DB = settings.CONFINDR_DB

logger = logging.getLogger('django')


# TODO: Implement this, not actually called by anything yet
def update_confindr_db() -> datetime.datetime:
    cmd = f"{CONFINDR_DB_SETUP} -s {CONFINDR_SECRET} -o {CONFINDR_DB}"
    logger.info(f"Updating confindr database with the following command: {cmd}")
    p = Popen(cmd, shell=True)
    p.wait()
    logger.info(f"Finished updating the database: {CONFINDR_DB}")

    # A file is automatically created for the download date,
    # but I think it's more robust to just generate a new datetime object manually.
    # download_date_file = CONFINDR_DB / 'download_date.txt'

    download_date = datetime.datetime.now()
    return download_date
