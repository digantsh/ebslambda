from __future__ import print_function
import boto3
import os
import json
import ast
import time
import datetime

sregion = os.environ['ActiveRegion']
# this can be passed as parameter to the lambda
dregion = os.environ['StandbyRegion']
env = os.environ['Environment']
tag = 'ArcherBackup' + env
volTag = tag + 'Volume'
snapTag = tag + 'Snap'

retention_days = int(os.environ['RetentionDays'])

client = boto3.client('ec2', region_name=sregion)
ec2 = boto3.resource('ec2', region_name=sregion, api_version = '2016-04-01')
accountId = boto3.client('sts').get_caller_identity().get('Account')
# latestsnap = ''
def lambda_handler(event, context):
    paginator = client.get_paginator('describe_snapshots')
    response_iterator = paginator.paginate(
        Filters=[
            {
                'Name': 'tag-key',
                'Values': [snapTag,]
            },
            {
                'Name': 'tag-value',
                'Values': ['Yes',]
            },
        ],
        OwnerIds=[
            accountId,
        ],
        # RestorableByUserIds=[
        #     'string',
        # ],
        # SnapshotIds=[
        #     'string',
        # ],
        DryRun=False,
        PaginationConfig={
            'MaxItems': 10000,
            'PageSize': 10000
            # 'StartingToken': 'string'
        }
    )
    # snapshots = response['Snapshots']
    list_of_snaps = []
    for page in response_iterator:
        for snapshot in page['Snapshots']:
            snapshotId =snapshot['SnapshotId']
            snapshotDate=snapshot['StartTime']
            list_of_snaps.append({'date':snapshotDate, 'snap_id': snapshotId})

    print(list_of_snaps)
    latestsnap = sorted(list_of_snaps, key=lambda k: k['date'], reverse=True)[0]['snap_id']
    print("latest snapshot is : %s" % latestsnap)

    ec2 = boto3.client('ec2', region_name=dregion)
    cp_Snap = ec2.copy_snapshot(
        Description='Copied Archer snapshot from ActiveRegion to StandbyRegion',
        DestinationRegion=dregion,
        SourceRegion=sregion,
        SourceSnapshotId=latestsnap,
    )
    print(cp_Snap)
    ec2 = boto3.resource('ec2', region_name=dregion, api_version = '2016-04-01')
    delete_date = datetime.date.today() + datetime.timedelta(days=retention_days)
    delete_fmt = delete_date.strftime('%Y-%m-%d')
    snapShotId=ec2.Snapshot(cp_Snap['SnapshotId'])
    tag = snapShotId.create_tags(
              DryRun=False,
              Tags=[
                  {
                      'Key': snapTag,
                      'Value': 'Yes'
                  },
                  {
                      'Key': 'ArcherDeleteOn',
                      'Value': delete_fmt
                  },
                  {
                      'Key': 'Name',
                      'Value': snapTag
                  },
                  {
                      'Key': 'Type',
                      'Value': 'Automated'
                  },
              ]
          )
if __name__ == '__main__':
    lambda_handler(None, None)
