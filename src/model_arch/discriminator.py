import torch 
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable

class Discriminator_Agnostic(nn.Module):
    def __init__(self, input_length: int, problem=None):
        super(Discriminator_Agnostic, self).__init__()
        self.problem = problem
        self.hidden = nn.Linear(input_length, 64)   # hidden layer
        self.hidden1 = nn.Linear(64, 32)   # hidden layer
        self.hidden2 = nn.Linear(32, 32)   # hidden layer
        self.hidden3 = nn.Linear(256, 128)   # hidden layer
        self.hidden4 = nn.Linear(128, 64)   # hidden layer
        self.hidden5 = nn.Linear(64, 32)   # hidden layer
        self.predict = nn.Linear(32, 1)   # output layer
        self.predict_classify = nn.Linear(32, 2)   # output layer

        self.dropout = nn.Dropout(0.25)
        self.sig = nn.Sigmoid()
        self.bn1 = nn.BatchNorm2d(64), #applying batch norm
        self.ln1 = nn.LayerNorm(1)
        self.soft = nn.Softmax(dim=1)
        self.problem = problem

        

    def forward(self, x):

        if self.problem == "classification":
            x = F.leaky_relu(self.hidden(x))
            x = self.dropout(x)
            x = F.leaky_relu(self.hidden1(x))
            x = self.dropout(x)
            for i in range(8):
                x = F.leaky_relu(self.hidden2(x))
                x = self.dropout(x)
            x = self.predict_classify(x)
            x = self.soft(x)
            # x = self.dropout(x)
            return x

        x = F.leaky_relu(self.hidden(x))
        x = self.dropout(x)
        x = self.predict(x)

        return x

class Discriminator_Law(nn.Module):
    def __init__(self, input_length: int, problem=None):
        super(Discriminator_Law, self).__init__()
        self.problem = problem
        epsilon = 1
        dim1 = 32
        dim2 = 16
        finaldim = 16
        self.hidden = torch.nn.Linear(input_length, dim1)   # hidden layer
        self.hidden1 = torch.nn.Linear(dim1, dim2)   # hidden layer
        self.hidden2 = torch.nn.Linear(dim2, finaldim)   # hidden layer
        self.predict = torch.nn.Linear(finaldim, 1)   # output layer
        self.dropout = nn.Dropout(0.75)
    def forward(self, x):
        x = F.leaky_relu(self.hidden(x))
        x = self.dropout(x)
        x = F.leaky_relu(self.hidden1(x))
        x = self.dropout(x)
        x = self.predict(x)
        return x
    