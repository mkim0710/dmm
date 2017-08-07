import os,time,sys
import fcntl,errno
import socket
sys.path.append('../')
from datasets.load import loadDataset
from parse_args import params 
from utils.misc import removeIfExists,createIfAbsent,mapPrint,saveHDF5,displayTime,getLowestError

if params['dataset']=='':
    params['dataset'] = 'jsb'
dataset = loadDataset(params['dataset'])
params['savedir']+='-'+params['dataset']
createIfAbsent(params['savedir'])

#Saving/loading
for k in ['dim_observations','dim_actions','data_type']:
    params[k] = dataset[k]
mapPrint('Options: ',params)

start_time = time.time()
from   model_th.dmm import DMM
import model_th.learning as DMM_learn
import model_th.evaluate as DMM_evaluate
displayTime('import DMM',start_time, time.time())
dmm = None

#Remove from params
start_time = time.time()
removeIfExists('./NOSUCHFILE')
reloadFile = params.pop('reloadFile')
if os.path.exists(reloadFile):
    pfile=params.pop('paramFile')
    assert os.path.exists(pfile),pfile+' not found. Need paramfile'
    print 'Reloading trained model from : ',reloadFile
    print 'Assuming ',pfile,' corresponds to model'
    dmm  = DMM(params, paramFile = pfile, reloadFile = reloadFile) 
else:
    pfile= params['savedir']+'/'+params['unique_id']+'-config.pkl'
    print 'Training model from scratch. Parameters in: ',pfile
    dmm  = DMM(params, paramFile = pfile)
displayTime('Building dmm',start_time, time.time())

savef     = os.path.join(params['savedir'],params['unique_id']) 
print 'Savefile: ',savef
start_time= time.time()
savedata = DMM_learn.learn(dmm, dataset['train'], dataset['mask_train'], 
                                epoch_start =0 , 
                                epoch_end = params['epochs'], 
                                batch_size = params['batch_size'],
                                savefreq   = params['savefreq'],
                                savefile   = savef,
                                dataset_eval=dataset['valid'],
                                mask_eval  = dataset['mask_valid'],
                                replicate_K= params['replicate_K'],
                                shuffle    = False
                                )
displayTime('Running DMM',start_time, time.time()         )
dmm = None
""" Load the best DMM based on the validation error """
epochMin, valMin, idxMin = getLowestError(savedata['valid_bound'])
reloadFile= pfile.replace('-config.pkl','')+'-EP'+str(int(epochMin))+'-params.npz'
print 'Loading from : ',reloadFile
params['validate_only']          = True
dmm_best                         = DMM(params, paramFile = pfile, reloadFile = reloadFile)
additional                       = {}
savedata['bound_test_best']      = DMM_evaluate.evaluateBound(dmm_best,  dataset['test'], dataset['mask_test'], S = 2, batch_size = params['batch_size'], additional =additional) 
savedata['ll_test_best']         = DMM_evaluate.impSamplingNLL(dmm_best, dataset['test'], dataset['mask_test'], S = 2000, batch_size = params['batch_size'])
saveHDF5(savef+'-final.h5',savedata)
print 'Experiment Name: <',params['expt_name'],'> Test Bound: ',savedata['bound_test_best'],' ',savedata['bound_tsbn_test_best'],' ',savedata['ll_test_best']