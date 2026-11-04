import math

class Neuron:
    def __init__(self, bias, layer, address):
        self.bias = bias
        self.value = 0
        self.inqueue = []
        self.outsynapses = []
        self.insynapses = []
        self.layer, self.address = layer,address
        
    def evaluate(self):
        self.value = self.squish(sum(self.inqueue)+self.bias)
        
    def squish(self, number):
        if len(self.insynapses) == 0:
            return number
        elif len(self.outsynapses) == 0:
            return math.tanh(number)
        else:
            return max(0,number)
    
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
            neuronlayers.append(neuronlayer)
            if i != 0:
                synapselayer = []
                synapselayers.append(synapselayer)
            for j in range(sizes[i]):
                neuron = Neuron(initBiases[i][j], i,j)
                neuronlayer.append(neuron)
                if i != 0:
                    for k in range(sizes[i-1]):
                        synapselayer.append(Synapse(neuronlayers[i-1][k], neuron, initWeights[i-1][j][k]))
        self.neuronlayers = neuronlayers
        self.synapselayers = synapselayers
        
    def evaluateInput(self, data):
        for i in range(len(data)):
            self.neuronlayers[0][i].receive(data[i])
            self.neuronlayers[0][i].evaluate()
        for i in range(len(self.neuronlayers)-1):
            for j in self.synapselayers[i]:
                j.propogate()
            for j in self.neuronlayers[i+1]:
                j.evaluate()
        return [i.send() for i in self.neuronlayers[-1]]