import boto3
import re
import datetime
import os
region = os.environ['ActiveRegion']
ec = boto3.client('ec2', region_name = region)

iam = boto3.client('iam')
# looks at any/all snapshot that has a "ArcherDeleteOn" tag containing the current day formatted as YYYY-MM-DD. should run daily
def lambda_handler(event, context):
    client = boto3.client("sts")
    account_id = client.get_caller_identity()["Account"]
    delete_on = datetime.date.today().strftime('%Y-%m-%d')

    filters = [
        { 'Name': 'tag:ArcherDeleteOn', 'Values': [delete_on] },
        { 'Name': 'tag:Type', 'Values': ['Automated'] },
    ]
    snapshot_response = ec.describe_snapshots(OwnerIds=[account_id], Filters=filters)

    for snap in snapshot_response['Snapshots']:
        for tag in snap['Tags']:
            if tag['Key'] != 'KeepForever':
                skipping_this_one = False
                continue
            else:
                skipping_this_one = True

        if skipping_this_one == True:
            print "Skipping snapshot %s (marked KeepForever)" % snap['SnapshotId']
            # do nothing else
        else:
            print "Deleting snapshot %s" % snap['SnapshotId']
            ec.delete_snapshot(SnapshotId=snap['SnapshotId'])
