import torch
import torch.nn as nn 
import pandas as pd
import yaml
import logging 
import sys 
import torch.nn.functional as F
import numpy as np

from tqdm import tqdm 
from discriminator import Discriminator_Agnostic, Discriminator_Awareness, Generator
from dfencoder.autoencoder import AutoEncoder
from sklearn import preprocessing
from dfencoder.dataframe import EncoderDataFrame

def train(**parameters):
    """Hyperparameter"""
    learning_rate = parameters['learning_rate']
    epochs = parameters['epochs']
    input_length = parameters['input_length']
    dataframe = parameters['dataframe']

    generator = AutoEncoder(input_length)
    discriminator_agnostic = Discriminator_Agnostic(input_length)
    discriminator_awareness = Discriminator_Awareness(input_length)

    """Optimizer"""
    generator_optimizer = torch.optim.Adam(generator.parameters(), lr=learning_rate)
    discriminator_agnostic_optimizer = torch.optim.Adam(
        discriminator_agnostic.parameters(), lr=learning_rate
    )
    discriminator_awareness_optimizer = torch.optim.Adam(
        discriminator_awareness.parameters(), lr=learning_rate
    )


    """Loss function"""
    loss = nn.BCELoss()


    """Training steps"""
    for i in tqdm(epochs):
        X = dataframe['normal_features']
        S = dataframe['sensitive_features']
        Y = dataframe['target']

        Z = generator.generator_fit(X)
        
        predictor_agnostic = discriminator_agnostic.forward(Z)
        predictor_awareness = discriminator_awareness.forward(Z, S)

        loss_agnostic = loss(predictor_agnostic, Y)
        loss_awareness = loss(predictor_awareness, Y)
        final_loss = (loss_agnostic + loss_awareness) / 2
        final_loss.backward()

        generator_optimizer.step()
        discriminator_agnostic_optimizer.step()
        discriminator_awareness_optimizer.step()

if __name__ == "__main__":
    """Device"""
    if torch.cuda.is_available():
        dev = "cuda:0"
    else:
        dev = "cpu"
    device = torch.device(dev)

    """Load configuration"""
    with open("/home/trduong/Data/counterfactual_fairness_game_theoric/configuration.yml", 'r') as stream:
        try:
            conf = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
        
    """Set up logging"""
    logger = logging.getLogger('genetic')
    file_handler = logging.FileHandler(filename=conf['log_law'])
    stdout_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    file_handler.setFormatter(formatter)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stdout_handler)
    logger.setLevel(logging.DEBUG)
    

    """Load data"""
    data_path = conf['data_law']
    df = pd.read_csv(data_path)
    
    """Setup features"""
    sensitive_feature = ['race', 'sex']
    normal_feature = ['LSAT', 'UGPA']
    categorical_feature = ['race', 'sex']
    full_feature = sensitive_feature + normal_feature
    target = 'ZFYA'
    selected_race = ['White', 'Black']
    df = df[df['race'].isin(selected_race)]
    
    df = df.reset_index(drop = True)
    
    """Preprocess data"""
    df['LSAT'] = (df['LSAT']-df['LSAT'].mean())/df['LSAT'].std()
    df['UGPA'] = (df['UGPA']-df['UGPA'].mean())/df['UGPA'].std()
    df['ZFYA'] = (df['ZFYA']-df['ZFYA'].mean())/df['ZFYA'].std()
    
    le = preprocessing.LabelEncoder()
    df['race'] = le.fit_transform(df['race'])
    df['sex'] = le.fit_transform(df['sex'])
    df = df[['LSAT', 'UGPA', 'sex', 'race', 'ZFYA']]  
    
    df_generator = df[normal_feature]
    

    df = pd.get_dummies(df, columns = ['sex'])
    df = pd.get_dummies(df, columns = ['race'])

    # print(df)
    # df = pd.get_dummies(df.sex, prefix='Sex')
    sensitive_feature = ['sex_0','sex_1', 'race_0', 'race_1']
    # sys.exit(1)
    
    # X, y = df[['LSAT', 'UGPA', 'sex', 'race']].values, df['ZFYA'].values
    
    """Setup hyperparameter"""    
    logger.debug('Setup hyperparameter')
    parameters = {}
    parameters['epochs'] = 2
    parameters['learning_rate'] = 0.001
    parameters['dataframe'] = df
    parameters['batch_size'] = 256
    parameters['problem'] = 'regression'

    """Hyperparameter"""
    learning_rate = parameters['learning_rate']
    epochs = parameters['epochs']
    dataframe = parameters['dataframe']
    batch_size = parameters['batch_size']
    problem = parameters['problem']
    
    """Setup generator and discriminator"""
    emb_size = 128
    # generator = Generator(df_generator.shape[1])
    generator= AutoEncoder(
        encoder_layers=[512, 512, emb_size],  # model architecture
        decoder_layers=[],  # decoder optional - you can create bottlenecks if you like
        activation='relu',
        swap_p=0.2,  # noise parameter
        lr=0.001,
        lr_decay=.99,
        batch_size=512,  # 512
        verbose=False,
        optimizer='sgd',
        scaler='gauss_rank',  # gauss rank scaling forces your numeric features into standard normal distributions
    )        
    discriminator_agnostic = Discriminator_Agnostic(emb_size, problem)
    discriminator_awareness = Discriminator_Awareness(emb_size+len(sensitive_feature), problem)
    
    # generator.to(device)
    discriminator_agnostic.to(device)
    discriminator_awareness.to(device)

    """Setup generator"""
    df_generator = df[normal_feature]

    generator.build_model(df_generator)

    """Optimizer"""
    generator_optimizer = torch.optim.Adam(
        generator.parameters(), lr=learning_rate
    )
    
    discriminator_agnostic_optimizer = torch.optim.Adam(
        discriminator_agnostic.parameters(), lr=learning_rate
    )
    discriminator_awareness_optimizer = torch.optim.Adam(
        discriminator_awareness.parameters(), lr=learning_rate
    )
    
    
    """Training"""
    n_updates = len(df)// batch_size
    logger.debug('Training')
    logger.debug('Number of updates {}'.format(n_updates))
    logger.debug('Dataframe length {}'.format(len(df)))
    logger.debug('Batchsize {}'.format((batch_size)))
    
    loss = torch.nn.SmoothL1Loss()
    loss = torch.nn.MSELoss()


    
    epochs = 100
    # epochs = 1
    
    for i in (range(epochs)):
        # logger.debug('Epoch {}'.format((i)))  
        
        for j in tqdm(range(n_updates)):
            df_term_generator = df_generator.loc[batch_size*j:batch_size*(j+1)]
            df_term_generator = EncoderDataFrame(df_term_generator)
            df_term_discriminator = df.loc[batch_size*j:batch_size*(j+1)]
            
            X = torch.tensor(df_term_discriminator[normal_feature].values.astype(np.float32)).to(device)
            
            S = torch.Tensor(df_term_discriminator[sensitive_feature].values).to(device)
            Y = torch.Tensor(df_term_discriminator[target].values).to(device).reshape(-1,1)
            
            num, bin, cat = generator.forward(df_term_generator)
            encode_output = torch.cat((num , bin), 1)    
            Z = generator.encode(encode_output)
            
            # Z = generator(X)
            # print(Z)

            predictor_agnostic = discriminator_agnostic(Z)
            predictor_awareness = discriminator_awareness(Z,S)
                    
            loss_agnostic = loss(predictor_agnostic, Y)
            loss_awareness = loss(predictor_awareness, Y)
            final_loss = loss_agnostic + F.relu(loss_agnostic - loss_awareness)
            
            generator_optimizer.zero_grad()
            discriminator_agnostic_optimizer.zero_grad()
            discriminator_awareness_optimizer.zero_grad()
            
            final_loss.backward()

            generator_optimizer.step()
            discriminator_agnostic_optimizer.step()
            discriminator_awareness_optimizer.step()

        # if i % 10 == 0:
        logger.debug('Epoch {}'.format(i))        
        logger.debug('Loss Agnostic {}'.format(loss_agnostic))        
        logger.debug('Loss Awareness {}'.format(loss_awareness))
        logger.debug('Final loss {}'.format(final_loss))
        logger.debug('-------------------')
        
        
        # df_result = pd.read_csv(conf['result_law'])
        # X = torch.tensor(df_generator[normal_feature].values.astype(np.float32)).to(device)
        # Z = generator(X)
        # predictor_agnostic = discriminator_agnostic(Z)
        # df_result['inv_prediction'] = predictor_agnostic.cpu().detach().numpy().reshape(-1)
        
        num, bin, cat = generator.forward(df_generator)
        encode_output = torch.cat((num ,bin), 1)    
        Z = generator.encode(encode_output)
        predictor_agnostic = discriminator_agnostic(Z)
        
        df_result = pd.read_csv(conf['result_law'])
        df_result['inv_prediction'] = predictor_agnostic.cpu().detach().numpy().reshape(-1)
        df_result.to_csv(conf['result_law'], index = False)
    
    


    sys.modules[__name__].__dict__.clear()
    
        # sys.exit(1)



    
    