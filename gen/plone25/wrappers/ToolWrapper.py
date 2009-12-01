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

    def getObject(self, uid):
        '''Allow to retrieve an object from its unique identifier p_uid.'''
        return self.o.getObject(uid, appy=True)

    def getDiskFolder(self):
        '''Returns the disk folder where the Appy application is stored.'''
        return self.o.getProductConfig().diskFolder
# ------------------------------------------------------------------------------
