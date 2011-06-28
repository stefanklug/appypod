'''job.py must be executed by a "zopectl run" command and, as single arg,
   must get a string with the following format:

    <ZopeAdmin>:<PloneInstancePath>:<ApplicationName>:<ToolMethodName>[:<args>].

     <ZopeAdmin> is the userName of the Zope administrator for this instance.
     <PloneInstancePath> is the path, within Zope, to the Plone Site object (if
                         not at the root of the Zope hierarchy, use '/' as
                         folder separator);

     <ApplicationName> is the name of the Appy application. If it begins with
                       "path=", it does not represent an Appy application, but
                       the path, within <PloneInstancePath>, to any Zope object
                       (use '/' as folder separator)

     <ToolMethodName> is the name of the method to call on the tool in this
                      Appy application, or the method to call on the arbitrary
                      Zope object if previous param starts with "path=".

     <args> (optional) are the arguments to give to this method (only strings
            are supported). Several arguments must be separated by '*'.

    Note that you can also specify several commands, separated with
    semicolons (";"). This scripts performes a single commit after all commands
    have been executed.
'''

# ------------------------------------------------------------------------------
import sys, transaction

# Check that job.py is called with the right parameters.
if len(sys.argv) != 2:
    print 'job.py was called with wrong args.'
    print __doc__
else:
    commands = sys.argv[1].split(';')
    # Check that every command has the right number of sub-elelements.
    for command in commands:
        parts = command.split(':')
        if len(parts) not in (4,5):
            print 'job.py was called with wrong args.'
            print __doc__

    for command in commands:
        parts = command.split(':')
        # Unwrap parameters
        if len(parts) == 4:
            zopeUser, plonePath, appName, toolMethod = parts
            args = ()
        else:
            zopeUser, plonePath, appName, toolMethod, args = parts
        # Zope was initialized in a minimal way. Complete Zope install.
        from Testing import makerequest
        app = makerequest.makerequest(app)
        # Log as Zope admin
        from AccessControl.SecurityManagement import newSecurityManager
        user = app.acl_users.getUserById(zopeUser)
        if not hasattr(user, 'aq_base'):
            user = user.__of__(app.acl_users)
        newSecurityManager(None, user)
        # Get the Plone site
        ploneSite = app # Initialised with the Zope root object.
        for elem in plonePath.split('/'):
            ploneSite = getattr(ploneSite, elem)
        # If we are in a Appy application, the object on which we will call the
        # method is the tool within this application.
        if not appName.startswith('path='):
            objectName = 'portal_%s' % appName.lower()
            targetObject = getattr(ploneSite, objectName).appy()
        else:
            # It can be any object within the Plone site.
            targetObject = ploneSite
            for elem in appName[5:].split('/'):
                targetObject = getattr(targetObject, elem)
        # Execute the method on the target object
        if args: args = args.split('*')
        exec 'targetObject.%s(*args)' % toolMethod
    transaction.commit()
# ------------------------------------------------------------------------------
