from appy.gen import *

class Meeting:
    place = String(editDefault=True)
    date = Date()
    myObservations = String(format=String.XHTML, optional=True)
    annex = File(optional=True)
    leader = String(validator=['andyStein', 'joelLambillotte'])
    root = True
    pod = ['Meeting']
