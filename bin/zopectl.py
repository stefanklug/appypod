# ------------------------------------------------------------------------------
import sys, os, os.path
import Zope2.Startup.zopectl as zctl

# ------------------------------------------------------------------------------
class ZopeRunner:
    '''This class allows to run a Appy/Zope instance.'''

    def run(self):
        # Check that an arg has been given (start, stop, fg, run)
        if not sys.argv[3].strip():
            print('Argument required.')
            sys.exit(-1)
        # Identify the name of the application for which Zope must run.
        app = os.path.splitext(os.path.basename(sys.argv[2]))[0].lower()
        # Launch Zope.
        options = zctl.ZopeCtlOptions()
        options.realize(None)
        options.program = ['/usr/bin/%srun' % app]
        options.sockname = '/var/lib/%s/zopectlsock' % app
        c = zctl.ZopeCmd(options)
        c.onecmd(" ".join(options.args))
        return min(c._exitstatus, 1)
# ------------------------------------------------------------------------------
