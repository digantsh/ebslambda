from __future__ import print_function
import boto3
import os
import json
import ast
import time
import datetime

sregion = os.environ['ActiveRegion']
dregion = os.environ['StandbyRegion']

# sregion = 'us-east-1'
# dregion = 'us-west-2'
retention_days = int(os.environ['RetentionDays'])
# retention_days = 7
# sregion='us-west-2'
# dregion='us-east-1'
client = boto3.client('ec2', region_name=sregion)
ec2 = boto3.resource('ec2', region_name=sregion, api_version = '2016-04-01')
accountId = boto3.client('sts').get_caller_identity().get('Account')
latestsnap = ''

def getLatestSnap():
    response = client.describe_snapshots(
        OwnerIds=[
            accountId
        ],
        Filters=[
            {
                'Name': 'tag-key',
                'Values': ['ArcherBackupSnap',]
            },
            {
                'Name': 'tag-value',
                'Values': ['Yes',]
            },
        ],
        MaxResults = 10000
    )
    snapshots = response['Snapshots']
    list_of_snaps = []
    for snapshot in snapshots:
        snapshotId =snapshot['SnapshotId']
        snapshotDate=snapshot['StartTime']
        list_of_snaps.append({'date':snapshotDate, 'snap_id': snapshotId})
    # get latest snapshot out of all snapshots with same tags
    # if list_of_snaps == []:
    #     print("No snapshots available in ArcherBackupSnap tag in region :%s" %sregion)
    #     latestsnap = 'Nothing'
    #     return latestsnap
    # else:
    latestsnap = sorted(list_of_snaps, key=lambda k: k['date'], reverse=True)[0]['snap_id']
    print("latest snapshot is : %s" % latestsnap)
    return latestsnap
def createVolume(msg):
    # if latestsnap is not "Nothing":
    volume = client.create_volume(
        AvailabilityZone=msg['Details']['Availability Zone'],
        Encrypted=True,
        VolumeType='gp2',
        SnapshotId=getLatestSnap()
    )
    waiter = client.get_waiter('volume_available')
    waiter.wait(VolumeIds=[volume['VolumeId']])
    # time.sleep(30)
    # print(volume)
    print(type(volume))
    vol=ec2.Volume(volume['VolumeId'])
    vol.create_tags(Tags=[{'Key':'ArcherBackupVolume', 'Value':'Yes'}, {'Key': 'Name', 'Value':'Archer FS Volume'}])
    print(vol)
    return vol
    # else:
    #     print("Not Volume can be created with empty snapshot")
    #     vol = "Nothing"
    #     return vol

def createSnap():
    descVol = client.describe_volumes(
        Filters=[
            {
                'Name': 'tag-key',
                'Values': ['ArcherBackupVolume',]
            },
            {
                'Name': 'tag-value',
                'Values': ['Yes',]
            },
        ],
        MaxResults = 10000
    )
    if descVol['Volumes'] == []:
        print("No Volumes available with ArcherBackupVolume tag")
    else:
        snap = client.create_snapshot(
            VolumeId=descVol['Volumes'][0]['VolumeId'],
            Description='Snapshot Archer Terminate Event'
            )

        if (snap):
            print("\t\tSnapshot %s created in %s " % ( snap['SnapshotId'], sregion))
        shot=ec2.Snapshot(snap['SnapshotId'])
        delete_date = datetime.date.today() + datetime.timedelta(days=retention_days)
        delete_fmt = delete_date.strftime('%Y-%m-%d')
        tag = shot.create_tags(
            DryRun=False,
            Tags=[
                {
                    'Key': 'ArcherBackupSnap',
                    'Value': 'Yes'
                },
                {
                    'Key': 'ArcherDeleteOn',
                    'Value': delete_fmt
                },
                {
                    'Key': 'Name',
                    'Value': 'Archer Backup Snapshots'
                },
            ]
        )
        if snap['SnapshotId']:
            response = client.delete_volume(
                VolumeId=descVol['Volumes'][0]['VolumeId'],
                DryRun=False
                )
        print("Volume %s is deleted" % descVol['Volumes'][0]['VolumeId'])

def lambda_handler(event, context):
    message = event['Records'][0]['Sns']['Message']
    print(type(message))
    msg = ast.literal_eval(message)
    print(msg)
    if 'autoscaling:EC2_INSTANCE_LAUNCH' in msg['Event']:
        if 'Launching' in msg['Description']:
            print("Instance is Launching")
            vol = createVolume(msg)
            # if vol is not "Nothing":
            resp = vol.attach_to_instance(
                Device='xvdp',
                InstanceId=msg['EC2InstanceId'],
                DryRun=False
                )
            print(resp)
            # else:
            #     print("No Volume available to attach to instance :%s" % msg['EC2InstanceId'])
    elif 'autoscaling:TEST_NOTIFICATION' in msg['Event']:
        print("Autoscalling group still getting launched :" + msg['AutoScalingGroupName'])
    elif 'autoscaling:EC2_INSTANCE_TERMINATE' in msg['Event']:
        print("Termination Event - Do nothing")
        createSnap()
    else:
        print("Test Notificatin could be ERROR - Exiting")
