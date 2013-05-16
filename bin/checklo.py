'''This script allows to check the generation of PDF files via LibreOffice.'''
import sys, os.path
import appy

# ------------------------------------------------------------------------------
usage = '''Usage: python checklo.py [port]

If port is not speficied, it defaults to 2002.'''

# ------------------------------------------------------------------------------
class LoChecker:
    def __init__(self, port):
        self.port = port
        # Get an ODT file from the pod test suite.
        self.appyFolder = os.path.dirname(appy.__file__)
        self.odtFile = os.path.join(self.appyFolder, 'pod', 'test',
                                    'templates', 'NoPython.odt')

    def run(self):
        # Call LO in server mode to convert self.odtFile to PDF
        converter = os.path.join(self.appyFolder, 'pod', 'converter.py')
        cmd = 'python %s %s pdf -p %d' % (converter, self.odtFile, self.port)
        print cmd
        os.system(cmd)
        # Check if the PDF was generated
        pdfFile = '%s.pdf' % os.path.splitext(self.odtFile)[0]
        if not os.path.exists(pdfFile):
            print 'PDF was not generated.'
        else:
            os.remove(pdfFile)
            print 'Check successfull.'

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    nbOfArgs = len(sys.argv)
    if nbOfArgs not in (1, 2):
        print usage
        sys.exit()
    # Get the nb of args
    port = (nbOfArgs == 2) and int(sys.argv[1]) or 2002
    LoChecker(port).run()
# ------------------------------------------------------------------------------
