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


def pc_get_contacts(dept):
    '''Execute SQL stored procedure according to department code and return a list of contacts.'''
    contacts = []
    contacts_sproc = CONFIG['departments'][dept]['contacts_sproc']

    CURSOR.execute('exec ' + contacts_sproc)
    columns = [column[0] for column in CURSOR.description]
    for row in CURSOR.fetchall():
        contacts.append(dict(zip(columns, row)))

    return contacts


def pc_get_contact(pcid):
    contact = []

    CURSOR.execute('exec [Campus6].[custom].[CadenceSelContact] ?', pcid)
    columns = [column[0] for column in CURSOR.description]
    for row in CURSOR.fetchall():
        contact.append(dict(zip(columns, row)))

    return contact[0]


def pc_get_last_sync_state(dept):
    '''Return a list of contacts as they were last synced.'''
    contacts = []
    CURSOR.execute('exec cadence.selLastSyncState ?', dept)
    columns = [column[0] for column in CURSOR.description]
    for row in CURSOR.fetchall():
        contacts.append(dict(zip(columns, row)))

    return contacts


def cadence_get_contact(mobile):
    '''Get a contact from the Cadence API. Returns None of not found.'''
    try:
        r = HTTP_SESSION.get(api_url + '/v2/contacts/SS/' + mobile)
        r.raise_for_status()
        r = json.loads(r.text)
        return r
    except requests.HTTPError:
        # We can ignore 404 errors
        if r.status_code != 404:
            raise

    return None


def cadence_post_contacts(dept, import_batch):
    '''Create/update contact in Cadence and update local sync state table.'''
    r = HTTP_SESSION.post(api_url + '/v2/contacts/' +
                          dept + '/import', data=import_batch)
    r.raise_for_status()

    return r.status_code


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

for dept in CONFIG['departments']:
    # Fetch students from PowerCampus and nest inside sis dict
    # {'P000000000': {'sis': {'foo':'bar'}}}
    contacts = {}
    contacts = {k['PEOPLE_CODE_ID']: {'sis': k} for k in pc_get_contacts(dept)}

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
        if 'lss' in v and 'MobileNumber' in v['lss']:
            mobile = v['lss']['mobileNumber']
        elif 'sis' in v:
            # Might as well see if any SIS contacts were manually added at remote end
            mobile = v['sis']['mobileNumber']

        if mobile:
            remote = cadence_get_contact(mobile)
            if remote:
                contacts[k]['remote'] = remote

    # Build a new state for each contact
    # {'P000000000': {'ns': {'firstName': 'Foo', 'customFields': {'foo': 'bar'}},'lss': ...}}
    for k, v in contacts.items():
        # Get first/last names and mobile numbers from SIS
        base_fields = ['mobileNumber',
                       'uniqueCampusId',
                       'firstName',
                       'lastName',
                       'optedOut']
        if 'sis' in v:
            contacts[k]['ns'] = {
                kk: vv for (kk, vv) in v['sis'].items() if kk in base_fields}
            contacts[k]['ns']['custom_fields'] = {
                kk: v['sis'][kk] if kk in v['sis'] else None for kk in CONFIG['departments'][dept]['custom_fields']}
        else:
            # If contact not returned in bulk SIS query
            contact = pc_get_contact(k)
            contacts[k]['ns'] = {k: v for (k, v) in contact.items()}

        # Update opt-in/out status for each user that exists on remote
        if 'remote' in v:
            optin_local = pc_get_sms(k, dept)
            opt_newstate = eval_sync_state(
                optin_local, not v['remote']['optedOut'], not v['lss']['optedOut'])
            # Do something more with opt states?
            contacts[k]['ns']['optedOut'] = opt_newstate[0][0]

        # Copy custom fields from sis state or set to None if not exists

    # Send desired state to Cadence
    # https://api.mongooseresearch.com/docs/#operation/Import
    import_batch = {'notificationEmail': CONFIG['notification_email']}
    import_batch['contacts'] = [v['ns'] for k, v in contacts.items()]

    cadence_post_contacts(dept, import_batch)
