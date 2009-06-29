from appy.gen import *
from AppyCar.Interior.Radio import Radio

class RallyCarWorkflow:
    # Roles
    carDriver = 'CarDriver'
    driverM = ('Manager', carDriver)
    # Specific permissions
    readColor = ReadPermission('Car.color')
    writeColor = WritePermission('Car.color')
    # States
    created = State({r:driverM, w:driverM, d:driverM,
                     readColor: driverM, writeColor: driverM}, initial=True)
    running = State({r:driverM, w:driverM, d:driverM,
                     readColor: 'Manager', writeColor: 'Manager'})
    # Transitions
    run = Transition( (created, running), condition=driverM)
    stop = Transition( (running, created), condition=driverM)

class Car:
    sport = Boolean()
    color = String(specificReadPermission=True, specificWritePermission=True)
    description = String(format=String.TEXT)

class RallyCar(Car):
    root = True
    workflow = RallyCarWorkflow
    test = Integer()

class StandardRadio(Radio):
    test1 = Integer()

c = Config()
c.languages = ('en', 'fr')

class CarFlavour(Flavour):
    explanation = String(group="userInterface")
