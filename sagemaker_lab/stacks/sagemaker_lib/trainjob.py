# Fill in the values of these four variables
# arn_role=<arn-of-your-notebook-role>
# training_image=<training-image-for-region>
# bucket=<name-of-your-s3-bucket>
# region=<your-region>

# prefix=/sagemaker/videogames_xgboost
# training_job_name=videogames-xgboost-`date '+%Y-%m-%d-%H-%M-%S'`

# training_data=$bucket$prefix/train
# eval_data=$bucket$prefix/validation
# train_source={S3DataSource={S3DataType=S3Prefix,S3DataDistributionType=FullyReplicated,S3Uri=$training_data}}
# eval_source={S3DataSource={S3DataType=S3Prefix,S3DataDistributionType=FullyReplicated,S3Uri=$eval_data}}

# aws --region $region \
# sagemaker create-training-job \
# --role-arn $arn_role \
# --training-job-name $training_job_name \
# --algorithm-specification TrainingImage=$training_image,TrainingInputMode=File \
# --resource-config InstanceCount=1,InstanceType=ml.c4.2xlarge,VolumeSizeInGB=10 \
# --input-data-config ChannelName=train,DataSource=$train_source,CompressionType=None,ContentType=libsvm ChannelName=validation,DataSource=$eval_source,CompressionType=None,ContentType=libsvm \
# --output-data-config S3OutputPath=$bucket$prefix \
# --hyper-parameters max_depth=3,eta=0.1,eval_metric=auc,scale_pos_weight=2.0,subsample=0.5,objective=binary:logistic,num_round=100 \
# --stopping-condition MaxRuntimeInSeconds=1800
import os
import boto3
import json
import time

from aws_cdk import (
    aws_sagemaker as sagemaker,
)

# from sagemaker import AlgorithmEstimator
# from sagemaker.tuner import HyperparameterTuner

# data_path = os.path.join(DATA_DIR, 'marketplace', 'training')
# sagemaker.

# algo = AlgorithmEstimator(
#             algorithm_arn='arn:aws:sagemaker:us-east-2:764419575721:algorithm/scikit-decision-trees-1542410022',
#             role='SageMakerRole',
#             instance_count=1,
#             instance_type='ml.c4.xlarge',
#             sagemaker_session=sagemaker_session,
#             base_job_name='test-marketplace')

# train_input = algo.sagemaker_session.upload_data(
#     path=data_path, key_prefix='integ-test-data/marketplace/train')

# algo.set_hyperparameters(max_leaf_nodes=10)
# tuner = HyperparameterTuner(estimator=algo, base_tuning_job_name='some-name',
#                                 objective_metric_name='validation:accuracy',
#                                 hyperparameter_ranges=hyperparameter_ranges,
#                                 max_jobs=2, max_parallel_jobs=2)

# tuner.fit({'training': train_input}, include_cls_metadata=False)
# tuner.wait()
