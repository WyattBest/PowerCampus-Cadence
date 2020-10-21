
def has_changed(old, new):
    if old == new:
        return False
    else:
        return True


def eval_opt_states(l, r, s):
    """Return tuples of the target state of each argument and whether it has changed.
    Intended for deciding how to sync Opt-In flag, which can be changed from either end.
    The logic behind this is as follows:

    Local	Remote	LSS	XOR	Action
    0		0		0	0	None
    1		0		0	1	Remote and LSS = 1
    0		1		0	1	Local and LSS = 1
    0		0		1	1	LSS = 0
    1		0		1	0	Local and LSS = 0
    0		1		1	0	Remote and LSS = 0
    1		1		0	0	LSS = 1
    1		1		1	1	None

    Keyword arguments:
    l -- state of the local database
    r -- state of the remote database
    s -- last sync state
    """
    l = bool(l)
    r = bool(r)
    s = bool(s)

    # Nothing changed
    if l == r == s:
        return (l, False), (r, False), (s, False)
        # return results

    # If local and remote state differ
    if l ^ r:
        if l ^ r ^ s:
            return (True, has_changed(l, True)), (True, has_changed(r, True)), (True, has_changed(s, True))
        else:
            return (False, has_changed(l, False)), (False, has_changed(r, False)), (False, has_changed(s, False))
    # If remote and sync state differ
    elif r ^ s:
        return (r, has_changed(l, r)), (r, False), (r, has_changed(s, r))
    else:
        return (False, has_changed(l, False)), (False, has_changed(r, False)), (False, has_changed(s, False))


def eval_state(l, r, s):
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

    return state_dict.get((l, r, s))
