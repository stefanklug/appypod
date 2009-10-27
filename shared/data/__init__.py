'''This folder contains copies of external, "authentic" data, stored as text
   files, like ISO 639.2 country codes. In this package, corresponding Python
   classes are available for accessing the data in the text files.'''

# ------------------------------------------------------------------------------
import os, os.path

# ------------------------------------------------------------------------------
class Countries:
    '''This class gives access to the country codes as standardized by
       ISO-639. The file has been downloaded in July 2009 from
       http://www.loc.gov/standards/iso639-2/ascii_8bits.html (UTF-8 version)'''
    def __init__(self):
        self.fileName = os.path.dirname(__file__) + '/CountryCodesIso639.2.txt'
        self.languageCodes = []
        self.languageNames = []
        self.parseFile()

    def parseFile(self):
        '''Parses the language codes and names in the ISO file and puts them in
           self.languageCodes and self.languageNames.'''
        f = file(self.fileName)
        for line in f:
            if line.strip():
                lineElems = line.split('|')
                if lineElems[2].strip():
                    # I take only those that have a 2-chars ISO-639-1 code.
                    self.languageCodes.append(lineElems[2])
                    self.languageNames.append(lineElems[3])
        f.close()

    def exists(self, countryCode):
        '''Is p_countryCode a valid 2-digits country code?'''
        return countryCode in self.languageCodes

    def __repr__(self):
        i = -1
        res = ''
        for languageCode in self.languageCodes:
            i += 1
            res += 'Language: ' + languageCode + ' - ' + self.languageNames[i]
            res += '\n'
        return res

# ------------------------------------------------------------------------------
class BelgianCities:
    '''This class contains data about Belgian cities (postal codes). It creates
       a dictionary whose keys are postal codes and whose values are city names.
       The corresponding Excel file was downloaded on 2009-10-26 from
       https://www.post.be/site/fr/sse/advertising/addressed/biblio.html,
       converted to CSV (field separator being ";" field content is surrrounded
       by double quotes).'''
    def __init__(self):
        self.fileName = os.path.dirname(__file__) + '/BelgianCommunes.txt'
        self.data = {}
        self.parseFile()
    def parseFile(self):
        f = file(self.fileName)
        for line in f:
            if line.strip():
                lineElems = line.split(';')
                self.data[int(lineElems[0].strip('"'))]= lineElems[1].strip('"')
    def exists(self, postalCode):
        '''Is postalCode a valid Belgian postal code?'''
        return self.data.has_key(postalCode)
# ------------------------------------------------------------------------------
