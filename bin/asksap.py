'''This script allows to get information about a given SAP RFC function
   module.'''

# ------------------------------------------------------------------------------
import sys, getpass
from optparse import OptionParser
from appy.shared.sap import Sap, SapError

# ------------------------------------------------------------------------------
WRONG_NG_OF_ARGS = 'Wrong number of arguments.'
ERROR_CODE = 1
P_OPTION = 'The password related to SAP user.'
G_OPTION = 'The name of a SAP group of functions'

# ------------------------------------------------------------------------------
class AskSap:
    '''This script allows to get information about a given RCF function module
       exposed by a distant SAP system.

       usage: %prog [options] host sysnr client user functionName

       "host"         is the server name or IP address where SAP runs.
       "sysnr"        is the SAP system/gateway number (example: 0)
       "client"       is the SAP client number (example: 040)
       "user"         is a valid SAP login
       "sapElement"   is the name of a SAP function (the default) or a given
                      group of functions (if option -g is given). If -g is
                      specified, sapElement can be "_all_" and all functions of
                      all groups are shown.
       Examples
       --------
       1) Retrieve info about the function named "ZFX":
          python asksap.py 127.0.0.1 0 040 USERGDY ZFX -p passwd

       2) Retrieve info about group of functions "Z_API":
          python asksap.py 127.0.0.1 0 040 USERGDY Z_API -p passwd -g

       3) Retrieve info about all functions in all groups:
          python asksap.py 127.0.0.1 0 040 USERGDY _all_ -p passwd -g
    '''
    def manageArgs(self, parser, options, args):
        # Check number of args
        if len(args) != 5:
            print(WRONG_NG_OF_ARGS)
            parser.print_help()
            sys.exit(ERROR_CODE)

    def run(self):
        optParser = OptionParser(usage=AskSap.__doc__)
        optParser.add_option("-p", "--password", action='store', type='string',
            dest='password', default='', help=P_OPTION)
        optParser.add_option("-g", "--group", action='store_true',
            dest='isGroup', default='', help=G_OPTION)
        (options, args) = optParser.parse_args()
        try:
            self.manageArgs(optParser, options, args)
            # Ask the password, if it was not given as an option.
            password = options.password
            if not password:
                password = getpass.getpass('Password for the SAP user: ')
            connectionParams = args[:4] + [password]
            print('Connecting to SAP...')
            sap = Sap(*connectionParams)
            sap.connect()
            print('Connected.')
            sapElement = args[4]
            if options.isGroup:
                # Returns info about the functions available in this group of
                # functions.
                info = sap.getGroupInfo(sapElement)
                prefix = 'Group'
            else:
                # Return info about a given function.
                info = sap.getFunctionInfo(sapElement)
                prefix = 'Function'
            print('%s: %s' % (prefix, sapElement))
            print(info)
            sap.disconnect()
        except SapError, se:
            sys.stderr.write(str(se))
            sys.stderr.write('\n')
            sys.exit(ERROR_CODE)

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    AskSap().run()
# ------------------------------------------------------------------------------
