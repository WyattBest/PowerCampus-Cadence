from os import write
import requests
import json
import pyodbc


def pc_get_contacts(dept):
    '''Execute SQL stored procedure according to department code and return a list of contacts.'''
    contacts = []
    contacts_sproc = CONFIG['departments'][dept]['contacts_sproc']

    CURSOR.execute('exec ' + contacts_sproc + ' ?', dept)
    columns = [column[0] for column in CURSOR.description]
    for row in CURSOR.fetchall():
        contacts.append(dict(zip(columns, row)))

    return contacts


def pc_get_contact(pcid, dept):
    contact = []

    CURSOR.execute(
        'exec [Campus6].[custom].[CadenceSelContact] ?, ?', pcid, dept)
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


def pc_update_last_sync_state(dept, contacts):
    # Isolate data we want to insert
    columns = ['uniqueCampusId', 'mobileNumber', 'DepartmentCode', 'optedOut']
    data = []
    for c in contacts:
        if 'ns' in contacts[c] and contacts[c]['ns']['mobileNumber'] is not None:
            # Insert department code
            contacts[c]['ns']['DepartmentCode'] = dept
            # Append tuple to list
            data.append(
                tuple([v for (k, v) in contacts[c]['ns'].items() if k in columns]))

    # Delete existing dept records
    CURSOR.execute(
        'DELETE FROM [cadence].[LocalSyncState] WHERE DepartmentCode = ?', dept)

    # Insert new dept records
    sql = '''INSERT INTO [cadence].[LocalSyncState] (
        [PEOPLE_CODE_ID]
        ,[MobileNumber]
        ,[optedOut]
        ,[DepartmentCode]
        )
    VALUES (?, ?, ?, ?)'''
    CURSOR.executemany(sql, data)


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
    '''Create/update contact in Cadence.'''

    r = HTTP_SESSION.post(api_url + '/v2/contacts/' +
                          dept + '/import', json=import_batch)
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
CURSOR = CNXN.cursor()
CURSOR.fast_executemany = True
print(CNXN.getinfo(pyodbc.SQL_DATABASE_NAME))  # Print a test of connection

for dept in CONFIG['departments']:
    # Fetch students from PowerCampus and nest inside sis dict
    # {'P000000000': {'sis': {'foo':'bar'}}}
    contacts = {}
    contacts = {k['uniqueCampusId']: {'sis': k} for k in pc_get_contacts(dept)}

    # Add last sync state dict inside existing contacts dict
    # {'P000000000': {'lss': {'foo':'bar'}, 'sis': {'foo':'bar'}}}
    for k in pc_get_last_sync_state(dept):
        if k['uniqueCampusId'] in contacts:
            contacts[k['uniqueCampusId']]['lss'] = k
        else:
            contacts.update({k['uniqueCampusId']: {'lss': k}})

    # Build a new state for each contact who has an optedOut state
    # {'P000000000': {'ns': {'firstName': 'Foo', 'customFields': {'foo': 'bar'}},'lss': ...}}
    for k, v in contacts.items():
        # Get first/last names and mobile numbers from SIS
        base_fields = ['mobileNumber',
                       'uniqueCampusId',
                       'firstName',
                       'lastName',
                       'optedOut']
        if 'sis' in v and v['sis']['optedOut'] is not None:
            contacts[k]['ns'] = {
                kk: vv for (kk, vv) in v['sis'].items() if kk in base_fields}
            # Copy custom fields from sis state or set to None if not exists
            contacts[k]['ns']['customFields'] = {
                kk: v['sis'][kk] if kk in v['sis'] else vv for kk, vv in CONFIG['departments'][dept]['custom_fields'].items()}
        else:
            # If contact not returned in bulk SIS query, get individual records and set custom fields to None (old, unenrolled students)
            contact = pc_get_contact(k, dept)
            contacts[k]['ns'] = {k: v for (k, v) in contact.items()}
            contacts[k]['ns']['customFields'] = {
                kk: vv for kk, vv in CONFIG['departments'][dept]['custom_fields'].items()}

    # Send desired state to Cadence
    # https://api.mongooseresearch.com/docs/#operation/Import
    import_batch = {'notificationEmail': CONFIG['notification_email']}
    import_batch['contacts'] = [v['ns']
                                for k, v in contacts.items() if 'ns' in v and v['ns']['mobileNumber'] is not None]
    for contact in import_batch['contacts']:
        contact['allowMobileUpdate'] = 1

    # Update local sync state but do not commit SQL transaction.
    # Update remote state (Cadence). If successful, commit tran.
    # This can be improved by explicitly passing a connection around instead of depending on a global.
    pc_update_last_sync_state(dept, contacts)
    if cadence_post_contacts(dept, import_batch) == 200:
        CURSOR.commit()
