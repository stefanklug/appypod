# ------------------------------------------------------------------------------
def stringify(value):
    '''Transforms p_value such that it can be dumped as a string into a
        generated file.'''
    if isinstance(value, tuple) or isinstance(value, list):
        res = '('
        for v in value:
            res += '%s,' % stringify(v)
        res += ')'
    elif value.__class__.__name__ == 'DateTime':
        res = 'DateTime("%s")' % value.strftime('%Y/%m/%d %H:%M')
    else:
        res = str(value)
        if isinstance(value, basestring):
            if value.startswith('python:'):
                res = value[7:]
            else:
                res = "'%s'" % value.replace("'", "\\'")
                res = res.replace('\n', '\\n')
    return res

# ------------------------------------------------------------------------------
def updateRolesForPermission(permission, roles, obj):
    '''Adds roles from list p_roles to the list of roles that are granted
       p_permission on p_obj.'''
    from AccessControl.Permission import Permission
    # Find existing roles that were granted p_permission on p_obj
    existingRoles = ()
    for p in obj.ac_inherited_permissions(1):
        name, value = p[:2]
        if name == permission:
            perm = Permission(name, value, obj)
            existingRoles = perm.getRoles()
    allRoles = set(existingRoles).union(roles)
    obj.manage_permission(permission, tuple(allRoles), acquire=0)

# ------------------------------------------------------------------------------
def checkTransitionGuard(guard, sm, wf_def, ob):
    '''This method is similar to DCWorkflow.Guard.check, but allows to retrieve
       the truth value as a appy.gen.No instance, not simply "1" or "0".'''
    from Products.DCWorkflow.Expression import StateChangeInfo,createExprContext
    u_roles = None
    if wf_def.manager_bypass:
        # Possibly bypass.
        u_roles = sm.getUser().getRolesInContext(ob)
        if 'Manager' in u_roles:
            return 1
    if guard.permissions:
        for p in guard.permissions:
            if _checkPermission(p, ob):
                break
        else:
            return 0
    if guard.roles:
        # Require at least one of the given roles.
        if u_roles is None:
            u_roles = sm.getUser().getRolesInContext(ob)
        for role in guard.roles:
            if role in u_roles:
                break
        else:
            return 0
    if guard.groups:
        # Require at least one of the specified groups.
        u = sm.getUser()
        b = aq_base( u )
        if hasattr( b, 'getGroupsInContext' ):
            u_groups = u.getGroupsInContext( ob )
        elif hasattr( b, 'getGroups' ):
            u_groups = u.getGroups()
        else:
            u_groups = ()
        for group in guard.groups:
            if group in u_groups:
                break
        else:
            return 0
    expr = guard.expr
    if expr is not None:
        econtext = createExprContext(StateChangeInfo(ob, wf_def))
        res = expr(econtext)
        return res
    return 1
# ------------------------------------------------------------------------------
