'''job.py must be executed by a "zopectl run" command and, as single arg,
   must get a string with the following format:

    <PloneInstancePath>:<ApplicationName>:<ToolMethodName>[:<args>].

     <PloneInstancePath> is the path, within Zope, to the Plone Site object (if
                         not at the root of the Zope hierarchy, use '/' as
                         folder separator);

     <ApplicationName> is the name of the Appy application;

     <ToolMethodName> is the name of the method to call on the tool in this
                      Appy application;

     <args> (optional) are the arguments to give to this method (only strings
            are supported). Several arguments must be separated by '*'.'''

# ------------------------------------------------------------------------------
import sys
# Check that job.py is called with the right parameters.
if len(sys.argv) != 2:
    print 'job.py was called with wrong args.'
    print __doc__
else:
    command = sys.argv[1]
    parts = command.split(':')
    if len(parts) not in (3,4):
        print 'job.py was called with wrong args.'
        print __doc__
    else:
        # Unwrap parameters
        if len(parts) == 3:
            plonePath, appName, toolMethod = parts
            args = ()
        else:
            plonePath, appName, toolMethod, args = parts
        # Zope was initialized in a minimal way. Complete Zope and Plone
        # installation.
        from Testing import makerequest
        app = makerequest.makerequest(app)
        # Get the Plone site
        ploneSite = app # Initialised with the Zope root object.
        for elem in plonePath.split('/'):
            ploneSite = getattr(ploneSite, elem)
        # Get the tool corresponding to the Appy application
        toolName = 'portal_%s' % appName.lower()
        tool = getattr(ploneSite, toolName).appy()
        # Execute the method on the tool
        if args: args = args.split('*')
        exec 'tool.%s(*args)' % toolMethod
# ------------------------------------------------------------------------------
