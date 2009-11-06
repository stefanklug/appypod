# ------------------------------------------------------------------------------
class ToolWrapper:

    def getInitiator(self):
        '''Retrieves the object that triggered the creation of the object
           being currently created (if any).'''
        res = None
        initiatorUid = self.session['initiator']
        if initiatorUid:
            res = self.o.uid_catalog(UID=initiatorUid)[0].getObject().appy()
        return res
# ------------------------------------------------------------------------------
