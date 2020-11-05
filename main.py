import requests
import json
import pyodbc


def eval_sync_state(local, remote, sync):
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
    '''Return boolean of SMS Opt-In status in PowerCampus Telecommunications or None if nothing in Telecommunications.'''
    CURSOR.execute(
        '''select [STATUS] from [CAMPUS6].[DBO].[TELECOMMUNICATIONS]
             where [PEOPLE_ORG_CODE_ID] = ? AND [COM_TYPE] = ?''', pcid, 'SMS' + dept)
    row = CURSOR.fetchone()
    if row is not None:
        status = row.STATUS
        status_mapping = {'A': True, 'I': False}
        return status_mapping[status]
    else:
        return None


def pc_get_students():
    '''Return a list of students.'''
    sis_contacts = []
    CURSOR.execute('exec Campus6.[custom].[CadenceSelContacts]')
    columns = [column[0] for column in CURSOR.description]
    for row in CURSOR.fetchall():
        sis_contacts.append(dict(zip(columns, row)))

    return sis_contacts


def pc_get_last_sync_state(dept):
    '''Return a list of contacts as they were last synced.'''
    contacts = []
    CURSOR.execute('exec cadence.selLastSyncState ?', dept)
    columns = [column[0] for column in CURSOR.description]
    for row in CURSOR.fetchall():
        contacts.append(dict(zip(columns, row)))

    return contacts


def cadence_post_contact():
    '''Create/update contact in Cadence and update local sync state table.'''
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
# CNXN.autocommit = True
CURSOR = CNXN.cursor()
print(CNXN.getinfo(pyodbc.SQL_DATABASE_NAME))  # Print a test of connection

# Fetch students from PowerCampus and nest it inside a dict
# {'P000000000': {'sis': {'foo':'bar'}}}
contacts = {}
contacts = {k['PEOPLE_CODE_ID']: {'sis': k} for k in pc_get_students()}

for dept in CONFIG['dept_codes']:

    # Add last sync state dict inside existing contacts dict
    # {'P000000000': {'lss': {'foo':'bar'}, 'sis': {'foo':'bar'}}}
    for k in pc_get_last_sync_state(dept):
        if k['PEOPLE_CODE_ID'] in contacts:
            contacts[k['PEOPLE_CODE_ID']]['lss'] = k
        else:
            contacts.update({k['PEOPLE_CODE_ID']: {'lss': k}})

    # Add remote state dict inside existing contacts dict
    # Fetch each local contact from Cadence and add to dict with PCID as key
    # {'P000000000': {'remote': {'foo':'bar'}, 'sis': {'foo':'bar'}, ...}}
    for k, v in contacts.items():
        if 'MobileNumber' in v['lss']:
            mobile = v['lss']['MobileNumber']
        else:
            # Might as well see if any SIS contacts were manually added at remote end
            mobile = v['sis']['MobileNumber']

        r = HTTP_SESSION.get(api_url + '/v2/contacts/SS/' + mobile)
        r.raise_for_status()
        r = json.loads(r.text)
        contacts[k]['remote'] = r

    # Update opt-in/out status for each user
    for k, v in contacts.items():
        # If item exists on remote server
        if 'remote' in v:
            optin_local = pc_get_sms(k, dept)
            opt_newstate = eval_sync_state(
                optin_local, not v['remote']['optedOut'], not v['lss']['optedOut'])
            print(optin_local, not v['remote']
                  ['optedOut'], not v['lss']['optedOut'])
            print(opt_newstate)
            print('----')

    # Find new items to put into Cadence
    for k, v in contacts.items():
        if 'remote' not in v:
            cadence_post_contact()

    # If a contact's mobileNumber changed in SIS, update Cadence and LSS
    # for k, v in contacts.items():
    #     fields = ['firstName', 'lastName', 'mobileNumber']
    #     sis = v['sis']
    #     remote = v['remote']
    #     if 'mobileNumber' in sis and 'mobileNumber' in remote:
    #         if sis['mobileNumber'] != remote['mobileNumber']:
    #             cadence_post_contact()

