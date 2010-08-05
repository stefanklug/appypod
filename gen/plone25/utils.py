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
