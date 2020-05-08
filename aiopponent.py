def squish(number):
    return number

class Neuron:
    def __init__(self, bias):
        self.bias = bias
        self.value = 0
        self.inqueue = []
        self.outsynapses = []
        self.insynapses = []
        
    def evaluate(self):
        self.value = squish(sum(self.inqueue)+self.bias)
        
    def receive(self, value):
        self.inqueue.append(value)
        
    def send(self):
        return self.value
        
class Synapse:
    def __init__(self, axon, dendrite, weight):
        axon.outsynapses.append(self)
        dendrite.insynapses.append(self)
        self.axon = axon
        self.dendrite = dendrite
        self.weight = weight
        
    def propogate(self):
        value = self.axon.send()*self.weight
        self.dendrite.receive(value)
        
class Network:
    def __init__(self, sizes, initWeights, initBiases):
        neuronlayers = []
        synapselayers = []
        for i in range(len(sizes)):
            neuronlayer = []
            if i != 0:
                synapselayer = []
            for j in range(sizes[i]):
                neuron = Neuron(initBiases[i][j])
                neuronlayer.append(neuron)
                if i != 0:
                    for k in range(sizes[i-1]):
                        synapselayer.append(Synapse(neuronlayers[k], neuron, initWeights[i][j][k]))
        self.neuronlayers = neuronlayers
        self.synapselayers = synapselayers
        
    def evaluateInput(self, data):
        for i in range(len(data)):
            self.neuronlayers[0][i].receive(data[i])
        for i in range(len(self.neuronlayers)-1):
            for j in self.synapselayers[i]:
                j.propogate()
            for j in self.neuronlayers[i]:
                j.evaluate()
        return [i.send() for i in self.neuronlayers[-1]]
