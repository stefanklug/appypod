from appy.gen import *
class Zzz:
    root = True
    def show_f2(self): return True
    def validate_i2(self, value):
        if (value != None) and (value < 10):
            return 'Value must be higher or equal to 10.'
        return True
    title=String(multiplicity=(0,1), show=False)
    i1 = Integer(show=False)
    i2 = Integer(validator = validate_i2)
    f1 = Float(show=show_f2, page='other')
    f2 = Float(multiplicity=(1,1))

class SeveralStrings:
    root=True
    anEmail = String(validator=String.EMAIL)
    anUrl = String(validator=String.URL)
    anAlphanumericValue = String(validator=String.ALPHANUMERIC)
    aSingleSelectedValue = String(validator=['valueA', 'valueB', 'valueC'])
    aSingleMandatorySelectedValue = String(
        validator=['valueX', 'valueY', 'valueZ'], multiplicity=(1,1))
    aMultipleSelectedValue = String(
        validator=['valueS', 'valueT', 'valueU', 'valueV'],
        multiplicity=(1,None), searchable=True)
    aBooleanValue = Boolean(default=True)
    dateWithHour = Date()
    dateWithoutHour = Date(format=Date.WITHOUT_HOUR)
    anAttachedFile = File()
    anAttachedImage = File(isImage=True)

class Product:
    root = True
    description = String(format=String.TEXT)
    stock = Integer()
    def needOrder(self): return self.stock < 3
    def orderProduct(self): self.stock = 3
    order = Action(action=orderProduct, show=needOrder)

class Order:
    description = String(format=String.TEXT)
    number = Float(show=False)
    # Reference field
    def getReference(self): return 'OR-%f' % self.number
    reference = Computed(method=getReference)
    def filterProducts(self, allProducts):
        return [f for f in allProducts if f.description.find('Descr') != -1]
    products = Ref(Product, add=False, link=True, multiplicity=(1,None),
                   back=Ref(attribute='orders'), showHeaders=True,
                   shownInfo=('description','title', 'order'),
                   select=filterProducts)
    def onEdit(self, created):
        if created:
            import random
            self.number = random.random()

class Client:
    root = True
    folder = True
    title = String(show=False)
    firstName = String()
    name = String()
    orders = Ref(Order, add=True, link=False, multiplicity=(0,None),
                 back=Ref(attribute='client'), showHeaders=True,
                 shownInfo=('reference', 'description', 'products'), wide=True)
    def onEdit(self, created):
        self.title = self.firstName + ' ' + self.name
