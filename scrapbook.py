import_batch['contacts'] = {k: v for (k, v) in contacts.items(
) if k in fields or k in CONFIG['departments'][dept]}
for k, v in contacts.items():
    contact = {}
    contact['mobileNumber'] = v['sis']['Mobile']
    contact['uniqueCampusId'] = k
    contact['firstName'] = v['sis']['FirstName']
    contact['lastName'] = v['sis']['LastName']
    contact['optedOut'] = v['opt_newstate']
    contact['customFields'] = v[ns]
    contact['allowMobileUpdate'] = False


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

# Update opt-in/out status for each user that exists on remote.
# Example: ((False, True), (False, False), (False, True))
# ...user opted out in Cadence. SIS and LSS need to be changed.
if 'remote' in v:
    optin_local = pc_get_sms(k, dept)
    # Cadence considers True = Opt Out. We will use PowerCampus method, True = Opt In.
    opt_newstate = eval_sync_state(
        optin_local, not v['remote']['optedOut'], not v['lss']['optedOut'])
    # Store new state
    contacts[k]['ns']['optedOut'] = opt_newstate[0][0]
    # Update PowerCampus if necessary.
    if opt_newstate[0][1]:
        pc_update_opt()


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


# Dump request to JSON for debugging
debug = {'url': r.request.url,
         'method': r.request.method,
         'headers': dict(r.request.headers),
         'body': json.loads(r.request.body),
         'status_code': r.status_code,
         'text': r.text
         }
with open('request.json', mode='w') as file:
    json.dump(debug, file, indent=4)


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
