# -*- coding: utf-8 -*-
"""
Created on Wed Jul 13 11:11:12 2022

@author: anilb
"""
from flask import Flask, request, jsonify
import os
from werkzeug.utils import secure_filename
# from ibm_watson_machine_learning import APIClient
import tarfile
from datetime import datetime
# import time
import pandas as pd
from flask_cors import CORS, cross_origin
import codecs
import re
import requests
import subprocess
import json
from os.path import exists
from os.path import isfile, join
from os import listdir
    
    
app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

CODE_CONTAINER_PATH = "code_container"

def get_meta_of_file(path:str):
    try:
        meta_path = path.replace('.py','.meta')
        f = open(meta_path, 'r').read()
        j = json.loads(f)
        return j
    except:
        print("!!! get_meta_file error")

def check_file(p):
    if not exists(p):
        os.makedirs(p)
        
@app.route('/')
def home():
    return "Wellcome to MOE"

# NEED TO CHANGE THE PATH
@app.route('/saveModelFile', methods=['POST', 'GET'])
@cross_origin()
def saveModelOnServer():
    pythonFile = request.files['userNameModelFile']
    print(pythonFile)
    print(pythonFile.filename)
    # create the folders when setting up your app
    # os.makedirs(os.path.join(app.instance_path, ''), exist_ok=True)
    fileName = "modelName_" + request.args.get('user', type=str)+".ipynb"
    pythonFile.save(secure_filename(fileName))
    return "File Saved"


@app.route('/save-code', methods=['POST', 'GET'])
@cross_origin()
def saveCode():
    file_name = request.args.get('file-name', type=str)
    user_folder_name = request.args.get('user-folder', type=str)
    check_file(CODE_CONTAINER_PATH)
    user_folder_path = os.path.join(CODE_CONTAINER_PATH,user_folder_name)
    check_file(user_folder_path)
    file_path = os.path.join(user_folder_path,file_name)
    
    # Processing the code
    codeToSave = request.data.decode("utf-8")
    print(">>>>>\n",codeToSave)
    # codeToSave = codeToSave.replace("\",""")
    # print(f"{codeToSave}")
    codeUpdated = re.sub(r'\\.', lambda x: {
                         '\\n': '\n', '\\t': '\t'}.get(x[0], x[0]), codeToSave)
    codeUpdated = codeUpdated.replace('\\"', '"')
    codeUpdated = codeUpdated.replace('\\r', '')
    if(codeUpdated[0] == '"'):
        codeUpdated = codeUpdated[1:]
    if(codeUpdated[-1] == '"'):
        codeUpdated = codeUpdated[:-1]
        
    with open(file_path, "w") as f:
        f.write(codeUpdated)
    return codeUpdated


@app.route('/load-saved-code', methods=['POST'])
def loadSavedCode():
    print("=="*20,"\n",request.json)
    file_name = request.json['file-name']
    user_folder_name = request.json['user-folder']
    check_file(CODE_CONTAINER_PATH)
    user_folder_path = os.path.join(CODE_CONTAINER_PATH,user_folder_name)
    check_file(user_folder_path)
    file_path = os.path.join(user_folder_path,file_name)
    
    with open(file_path, 'r') as f:
        saved_code = f.read()
        return saved_code


@app.route('/convertToPyFormat')
def convert():
    """ Accepts fileName from URL """
    fileName = request.args.get('fileName', type=str)
    # Adding Extension
    fileName += ".ipynb"
    # fileName = 'Test1.ipynb'
    codeToConvert = "jupyter nbconvert --to script " + str(fileName)
    os.system(codeToConvert)
    return "File Converted"

@app.route('/get-list-files')
def get_list_files():
    """ Get list files of the user """
    user_folder_name = request.args.get('user-folder', type=str)
    print(request.args)
    check_file(CODE_CONTAINER_PATH)
    user_folder_path = os.path.join(CODE_CONTAINER_PATH,user_folder_name)
    check_file(user_folder_path)
    list_file_info = []
    for f in listdir(user_folder_path):
        full_path = join(user_folder_path, f)
        if not isfile(full_path) or not f.endswith(".py"): continue
        ts = os.stat(full_path).st_ctime
        list_file_info.append({'fileName':f,'createdAt':ts})
    return jsonify(list_file_info)


@app.route('/RunModelOnServer', methods=['POST', 'GET'])
def runModel():
    """ Accepts fileName from URL and will send logs for without errors"""
    # fileName=modelName_James
    fileName = request.args.get('fileName', type=str)
    # The command is 'Test1.py > Test1.txt'
    codeToRun = fileName + ".py" + " > " + fileName+".txt"
    # os.system('Test1.py > Test1.txt')
    os.system(codeToRun)
    codeToReadFile = fileName+".txt"
    # file = open("Test1.txt", "r")
    file = open(codeToReadFile, "r")
    contents = file.read()
    file.close()
    contents = str(contents)
    return contents


@app.route('/RunModelOnServer2', methods=['POST', 'GET'])
def runModel2():
    """ To get the error logs along with program logs """
    import time
    # fileName=modelName_James
    fileName = request.args.get('fileName', type=str)

    st = time.time()
    cmd = "python " + fileName+".py"
    # Starting process
    process = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Getting the output and errors of the program
    stdout, stderr = process.communicate()
    # file = open("Test1.txt", "r")
    stdout = stdout.decode("utf-8")
    stderr = stderr.decode("utf-8")
    et = time.time()
    allLogs = stdout + "\n" + stderr
    file = open("LogmodelFile.txt", "w")
    file.write(allLogs)
    file.close()
    return allLogs


@app.route('/deployModelToIBM')
def deployModelToIBM():
    # Adding the user name and model name to the deployment
    fileName = request.args.get('fileName', type=str)
    # File name required To convert the file to .tar file
    tarFileName = fileName+".tar.gz"
    # Adding Extension to upload in ibm cloud
    fileName += ".py"
    wml_credentials = {
        "apikey": "J9tngeD9LWUcLxyzbTAlQ6HNWwR-2_pEVhw0FdQ2nGjI",
        "url": "https://eu-gb.ml.cloud.ibm.com"
    }

    client = APIClient(wml_credentials)

    def reset(tarinfo):
        tarinfo.uid = tarinfo.gid = 0
        tarinfo.uname = tarinfo.gname = "root"
        return tarinfo
    # tar = tarfile.open("ADC.tar.gz", "w:gz")
    tar = tarfile.open(tarFileName, "w:gz")
    # add tar files here
    tar.add(fileName, arcname=fileName, filter=reset)
    tar.close()
    SPACE_ID = "f62b6f9c-3395-4918-93c9-88597e632940"
    client.set.default_space(SPACE_ID)
    softwareSpecId = client.software_specifications.get_uid_by_name(
        'do_20.1 with packages v7_1')

    # Pushing the model to IBM Platform
    # Getting Month Name
    monthDeployed = datetime.now().date().strftime("%B")
    DescriptionValue = "MetaOptimize Model for month :" + monthDeployed
    MODEL_ASSET_NAME = str(datetime.now()) + " " + fileName
    mnist_metadata = {
        client.repository.ModelMetaNames.NAME: MODEL_ASSET_NAME,
        client.repository.ModelMetaNames.DESCRIPTION: DescriptionValue,
        client.repository.ModelMetaNames.TYPE: "do-docplex_20.1",
        #client.repository.ModelMetaNames.SOFTWARE_SPEC_UID: client.software_specifications.get_uid_by_name("Brocolli")
        client.repository.ModelMetaNames.SOFTWARE_SPEC_UID: softwareSpecId
    }
    # It will store the model to the cloud space
    model_details = client.repository.store_model(
        model=tarFileName, meta_props=mnist_metadata)

    model_uid = client.repository.get_model_uid(model_details)

    # Deploying the model
    meta_props = {
        client.deployments.ConfigurationMetaNames.NAME: MODEL_ASSET_NAME,
        client.deployments.ConfigurationMetaNames.DESCRIPTION: DescriptionValue,
        client.deployments.ConfigurationMetaNames.BATCH: {},
        client.deployments.ConfigurationMetaNames.HARDWARE_SPEC: {
            'name': 'M', 'nodes': 4}
    }

    deployment_details = client.deployments.create(
        model_uid, meta_props=meta_props)

    deployment_uid = client.deployments.get_uid(deployment_details)

    print("Deployment uid:")
    print(deployment_uid)
    return "Model successfully deployed in the IBM Cloud, Deployment ID is =======> " + str(deployment_uid)




@app.route('/RunModelOnIBMCloud/<string:deployment_uid>')
def RunModelOnIBMCloud(deployment_uid):
    """ Accepts sceanrioId value from URL """
    # deployment_uid = request.args.get('fileName',type=str)
    scenario_id_value = request.args.get('scenarioId', type=str)
    if not scenario_id_value:
        scenario_id_value = '1'
    print(scenario_id_value)
    wml_credentials = {
        "apikey": "J9tngeD9LWUcLxyzbTAlQ6HNWwR-2_pEVhw0FdQ2nGjI",
        "url": "https://eu-gb.ml.cloud.ibm.com"
    }
    scenario_id = pd.DataFrame([scenario_id_value], columns=["scenario_id"])
    client = APIClient(wml_credentials)
    SPACE_ID = "f62b6f9c-3395-4918-93c9-88597e632940"

    client.set.default_space(SPACE_ID)

    deployment_uid = deployment_uid

    solve_payload = {client.deployments.DecisionOptimizationMetaNames.INPUT_DATA: [
        {
            "id": "scenario_id.csv",
            "values": scenario_id
        }
    ], client.deployments.DecisionOptimizationMetaNames.SOLVE_PARAMETERS:
        {'oaas.timeLimit': 3600000,
         'oaas.includeInputData': 'false',
         'oaas.logAttachmentName': 'log.txt',
         'oaas.logTailEnabled': 'true',
         'oaas.resultsFormat': 'JSON'},
        client.deployments.DecisionOptimizationMetaNames.OUTPUT_DATA: [
        {
            "id": ".*"
        }]
    }

    job_details = client.deployments.create_job(deployment_uid, solve_payload)
    job_uid = client.deployments.get_job_uid(job_details)
    # scenario_job_dict['scenario_job_dict'] = job_uid

    return "Job Created, Job Id is ------------> " + str(job_uid)


if __name__ == '__main__':
    app.debug = True
    app.run(host="0.0.0.0",port=9101)
