from os import stat, stat_result, truncate
import requests
import json
import pyodbc

from requests.models import HTTPBasicAuth


def has_changed(old, new):
    if old == y:
        return False
    else:
        return True


def eval_opt_state(local, remote, sync):
    """Return tuple of the target state of each argument and whether it has changed.
    Intended for deciding how to sync Opt-In flag, which can be changed from either end.
    The logic behind this is as follows:

    Local	Remote	LSS	Action
    0		0		0	None
    1		0		0	Remote and LSS = 1
    0		1		0	Local and LSS = 1
    0		0		1	LSS = 0
    1		0		1	Local and LSS = 0
    0		1		1	Remote and LSS = 0
    1		1		0	LSS = 1
    1		1		1	None

    Keyword arguments:
    local -- state of the local database
    remote -- state of the remote database
    sync -- last sync state
    """
    state_dict = {
        (0, 0, 0):	((0, 0), (0, 0), (0, 0)),
        (1, 0, 0):	((1, 0), (1, 1), (1, 1)),
        (0, 1, 0):	((1, 1), (1, 0), (1, 1)),
        (0, 0, 1):	((0, 0), (0, 0), (0, 1)),
        (1, 0, 1):	((0, 1), (0, 0), (0, 1)),
        (0, 1, 1):	((0, 0), (0, 1), (0, 1)),
        (1, 1, 0):	((1, 0), (1, 0), (1, 1)),
        (1, 1, 1):	((1, 0), (1, 0), (1, 0))
    }
    result = state_dict.get((local, remote, sync))

    # Turn 1 and 0 into True and False
    result = tuple(tuple(bool(kk) for kk in k) for k in result)

    return result


def pc_get_sms(pcid, dept):
    '''Return boolean of SMS Opt-In status in PowerCampus Telecommunications.'''
    CURSOR.execute('''SELECT [STATUS] FROM TELECOMMUNICATIONS WHERE PEOPLE_ORG_CODE_ID = ? AND COM_TYPE = 'SMS' + ?''',
                   pcid, dept)
    status = row['STATUS']
    if status == 'A':
        return True
    elif status == 'I':
        return False
    else:
        return None


with open('config_dev.json') as file:
    CONFIG = json.load(file)

api_url = CONFIG['api_url']
api_key = CONFIG['api_key']
api_secret = CONFIG['api_secret']
HTTP_SESSION = requests.Session()
HTTP_SESSION.auth = (api_key, api_secret)

# Microsoft SQL Server connection.
CNXN = pyodbc.connect(CONFIG['pc_database_string'])
CURSOR = CNXN.cursor()
print(CNXN.getinfo(pyodbc.SQL_DATABASE_NAME))  # Print a test of connection


for dept in CONFIG['dept_codes']:

    # Get local sync records from SQL and add to dict with PCID as key
    local_sync = []
    CURSOR.execute(
        'select top 10 * from [cadence].[Contacts] where DepartmentCode = ?', dept)
    columns = [column[0] for column in CURSOR.description]
    for row in CURSOR.fetchall():
        local_sync.append(dict(zip(columns, row)))
    local_sync = {k['PEOPLE_CODE_ID']: k for k in local_sync}

    # Fetch each local contact from Cadence and add to dict with PCID as key
    remote_contacts = {}
    for k, v in local_sync.items():
        mobile = v['MobileNumber']
        r = HTTP_SESSION.get(api_url + '/v2/contacts/SS/' + mobile)
        r.raise_for_status()
        r = json.loads(r.text)
        remote_contacts[r['contactId']] = r

    for k, v in local_sync.items():
        # If item exists on remote server
        if k in remote_contacts:
            opt = pc_get_sms(v['PEOPLE_CODE_ID'], 'SS')
            opt_target = eval_opt_state(opt, remote_contacts[k]['optedOut'], )
