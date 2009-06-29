from appy.gen import *

class BunchOfGeek:
    description = String(format=String.TEXT)

class ZopeComponentTool(Tool):
    someUsefulConfigurationOption = String()
    def onInstall(self):
        self.someUsefulConfigurationOption = 'My app is configured now!'
    install = Action(action=onInstall)

class ZopeComponentFlavour(Flavour):
    anIntegerOption = Integer()
    bunchesOfGeeks = Ref(BunchOfGeek, multiplicity=(0,None), add=True,
                         link=False, back=Ref(attribute='backToTool'),
                         shownInfo=('description',), page='data')
    def onEdit(self, created):
        if 'Escadron de la mort' not in [b.title for b in self.bunchesOfGeeks]:
            self.create('bunchesOfGeeks', title='Escadron de la mort',
                        description='I want those guys everywhere!')

class ZopeComponentWorkflow:
    # Specific permissions
    wf = WritePermission('ZopeComponent.funeralDate')
    rb = ReadPermission('ZopeComponent.responsibleBunch')
    # Roles
    zManager = 'ZManager'
    zLeader = 'ZLeader'
    managerM = (zManager, 'Manager')
    leaderM = (zLeader, 'Manager')
    everybody = (zManager, zLeader, 'Manager')
    # States
    created = State({r:leaderM, w:('Owner', 'Manager'), d:leaderM, wf:'Owner',
                     rb:everybody}, initial=True)
    validated = State({r:everybody, w:everybody, d:None, wf:everybody,
                       rb:everybody})
    underDevelopment = State({r:everybody, w:leaderM, d:None, wf:leaderM,
                              rb:everybody})
    whereIsTheClient = State({r:everybody, w:managerM, d:None, wf:managerM,
                             rb:everybody})
    # Transitions
    def funeralOk(self, obj): return obj.funeralDate
    validate = Transition( (created, validated),
                           condition=managerM + (funeralOk,))
    def updateDescription(self, obj):
        obj.description = 'Description edited by my manager was silly.'
    startDevelopment = Transition( (validated, underDevelopment),
                                   condition=leaderM, action=updateDescription)
    cancelDevelopment = Transition( (underDevelopment, whereIsTheClient),
                                    condition=managerM)
    cancel = Transition( ( (whereIsTheClient, underDevelopment),
                           (underDevelopment, validated),
                           (validated, created)), condition='Manager')

class ZopeComponent:
    root = True
    workflow = ZopeComponentWorkflow
    def showDate(self):
        return True
    def validateDescription(self, value):
        res = True
        if value.find('simple') != -1:
            res = self.translate('zope_3_is_not_simple')
        return res
    description = String(editDefault=True)
    technicalDescription = String(format=String.XHTML,
                                  validator=validateDescription)
    #status = String(validator=['underDevelopement', 'stillSomeWorkToPerform',
    #    'weAreAlmostFinished', 'alphaReleaseIsBugged', 'whereIsTheClient'],
    #    optional=True, editDefault=True)
    funeralDate = Date(optional=True, specificWritePermission=True)
    responsibleBunch = Ref(BunchOfGeek, multiplicity=(1,1), add=False,
                           link=True, back=Ref(attribute='components'),
                           specificReadPermission=True)

class CobolComponentWorkflow(ZopeComponentWorkflow):
    p = ZopeComponentWorkflow # Shortcut to workflow parent
    # An additional state
    finished = State(p.whereIsTheClient.permissions)
    # Override validate: condition on funeralDate has no sense here
    validate = Transition(p.validate.states, condition=p.managerM)
    # Override cancelDevelopment: go to finished instead
    cancelDevelopment = Transition( (p.underDevelopment, finished),
                                    condition=p.managerM)
    # Update cancel accordingly
    cancel = Transition( ((finished, p.underDevelopment),) +p.cancel.states[1:],
                         condition=p.cancel.condition)

class CobolComponent:
    root = True
    workflow = CobolComponentWorkflow
    description = String()

class Person:
    abstract = True
    pod = True
    title = String(show=False)
    n = 'name_3'
    firstName = String(group=n, width=15)
    middleInitial = String(group=n, width=3)
    name = String(multiplicity=(1,1), group=n, width=30)
    contractDetails = String(format=String.XHTML)
    cia = {'page': 'contactInformation', 'group': 'address_2'}
    street = String(**cia)
    number = Integer(**cia)
    country = String(**cia)
    zipCode = Integer(**cia)
    cio = {'page': 'contactInformation', 'group': 'numbers_2', 'width': 20}
    phoneNumber = String(**cio)
    faxNumber = String(**cio)
    mobilePhone = String(**cio)
    workPhoneNumber = String(**cio)
    workFaxNumber = String(**cio)
    workMobilePhone = String(**cio)
    def onEdit(self, created):
        self.title = self.firstName + ' ' + self.name

class Worker(Person):
    root = True
    productivity = Integer()

class Parasite(Person):
    root = True
    pod = ['SordidGossips', 'MoreGossips']
    hairColor = String(group='hairyCharacteristics')
    sordidGossips = String(format = String.XHTML, page='Gossips')
    parasiteIndex = String(validator=['low', 'medium', 'high',
                                      'unquantifiable'],
                           page='contactInformation', group='numbers')
    details = String(page='contactInformation', group='numbers',
                     master=parasiteIndex, masterValue='unquantifiable')
    avoidAnyPhysicalContact = Boolean(page='contactInformation')
    def validate(self, new, errors):
        if (new.hairColor == 'flashy') and (new.firstName == 'Gerard'):
            errors.hairColor = True
            errors.firstName = "Flashy Gerards are disgusting."

c = Config()
c.languages = ('en', 'fr')
c.defaultCreators += ['ZLeader']
