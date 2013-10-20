'''This script allows to generate a Zope product from a Appy application.'''

# ------------------------------------------------------------------------------
import sys, os.path
from optparse import OptionParser
from appy.gen.generator import GeneratorError, ZopeGenerator
from appy.shared.utils import LinesCounter
from appy.shared.packaging import Debianizer
import appy.version

# ------------------------------------------------------------------------------
ERROR_CODE = 1
APP_NOT_FOUND = 'Application not found at %s.'
WRONG_NG_OF_ARGS = 'Wrong number of arguments.'
C_OPTION = 'Removes from i18n files all labels that are not automatically ' \
           'generated from your gen-application. It can be useful during ' \
           'development, when you do lots of name changes (classes, ' \
           'attributes, states, transitions, etc): in this case, the Appy ' \
           'i18n label generation machinery produces lots of labels that ' \
           'then become obsolete.'
D_OPTION = 'Generates a Debian package for this app. The Debian package will ' \
           'be generated at the same level as the root application folder.'

class GeneratorScript:
    '''usage: %prog [options] app

       "app"          is the path to your Appy application, which must be a
                      Python package (= a folder containing a file named
                      __init__.py). Your app may reside anywhere, but needs to
                      be accessible by Zope. Typically, it may be or symlinked
                      in <yourZopeInstance>/lib/python.

       This command generates a Zope product in <app>/zope, which must be
       or symlinked in <yourZopeInstance>/Products.
    '''
    def manageArgs(self, parser, options, args):
        # Check number of args
        if len(args) != 1:
            print(WRONG_NG_OF_ARGS)
            parser.print_help()
            sys.exit(ERROR_CODE)
        # Check existence of application
        if not os.path.exists(args[0]):
            print(APP_NOT_FOUND % args[0])
            sys.exit(ERROR_CODE)
        # Convert app path to an absolute path
        args[0] = os.path.abspath(args[0])

    def run(self):
        optParser = OptionParser(usage=GeneratorScript.__doc__)
        optParser.add_option("-c", "--i18n-clean", action='store_true',
            dest='i18nClean', default=False, help=C_OPTION)
        optParser.add_option("-d", "--debian", action='store_true',
            dest='debian', default=False, help=D_OPTION)
        (options, args) = optParser.parse_args()
        try:
            self.manageArgs(optParser, options, args)
            print('Appy version: %s' % appy.version.verbose)
            print('Generating Zope product in %s/zope...' % args[0])
            ZopeGenerator(args[0], options).run()
            # Give the user some statistics about its code
            LinesCounter(args[0], excludes=['%szope' % os.sep]).run()
            # Generates a Debian package for this app if required
            if options.debian:
                app = args[0]
                appDir = os.path.dirname(app)
                appName = os.path.basename(app)
                # Get the app version from zope/version.txt
                f = file(os.path.join(app, 'zope', appName, 'version.txt'))
                version = f.read()
                f.close()
                version = version[:version.find('build')-1]
                Debianizer(app, appDir, appVersion=version).run()
        except GeneratorError, ge:
            sys.stderr.write(str(ge))
            sys.stderr.write('\n')
            optParser.print_help()
            sys.exit(ERROR_CODE)

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    GeneratorScript().run()
# ------------------------------------------------------------------------------
