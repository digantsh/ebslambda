import boto3
import collections
import datetime
import os

activeRegion = os.environ['ActiveRegion']
standbyRegion = os.environ['StandbyRegion']
# environment variable for dev/qa/prod
#env = os.environ['Environment']
env = 'dev'
tag = 'SnapBackup' + env
instTag = 'tag:' + tag + 'Instance'

volTag = tag + 'Volume'
snapTag = tag + 'Snap'
ec = boto3.client('ec2', region_name = activeRegion)
ec2 = boto3.resource('ec2', region_name=activeRegion, api_version = '2016-04-01')

def lambda_handler(event, context):
    reservations = ec.describe_instances(
        Filters=[
            { 'Name': instTag, 'Values': ['Yes'] },
            ]
        ).get(
            'Reservations', []
        )
    instances = sum(
        [
            [i for i in r['Instances']]
            for r in reservations
            ], [])
    print "Found %d instances that need backing up" % len(instances)
    to_tag = collections.defaultdict(list)
    for instance in instances:
        try:
            retention_days = [
                int(t.get('Value')) for t in instance['Tags']
                if t['Key'] == 'Retention'][0]

        except IndexError:
            retention_days = int(os.environ['RetentionDays'])
            # for dev in instance['BlockDeviceMappings']:
            descVol = ec.describe_volumes(
                Filters=[
                    {
                        'Name': 'tag-key',
                        'Values': [volTag,]
                    },
                    {
                        'Name': 'tag-value',
                        'Values': ['Yes',]
                    },
                ],
                MaxResults = 10000
            )
            if descVol['Volumes']==[]:
                continue
            # if dev.get('Ebs', None) is None:
                # continue
            vol_id = descVol['Volumes'][0]['VolumeId']
            dev_name = descVol['Volumes'][0]['Attachments'][0]['Device']
            print "\tFound EBS volume %s (%s) on instance %s" % (
                vol_id, dev_name, instance['InstanceId'])

            # figure out instance name if there is one
            instance_name = ""
            for tag in instance['Tags']:
                if tag['Key'] != 'Name':
                    continue
                else:
                    instance_name = tag['Value']

            description = '%s - %s (%s)' % ( instance_name, vol_id, dev_name )

            # trigger snapshot
            snap = ec.create_snapshot(
                VolumeId=vol_id,
                Description=description
                )

            if (snap):
                print "\t\tSnapshot %s created in %s of [%s]" % ( snap['SnapshotId'], activeRegion, description )
            to_tag[retention_days].append(snap['SnapshotId'])
            print "\t\tRetaining snapshot %s of volume %s from instance %s (%s) for %d days" % (
                snap['SnapshotId'],
                vol_id,
                instance['InstanceId'],
                instance_name,
                retention_days,
            )
            snapShotId=ec2.Snapshot(snap['SnapshotId'])
            delete_date = datetime.date.today() + datetime.timedelta(days=retention_days)
            delete_fmt = delete_date.strftime('%Y-%m-%d')
            tag = snapShotId.create_tags(
                DryRun=False,
                Tags=[
                    {
                        'Key': snapTag,
                        'Value': 'Yes'
                    },
                    {
                        'Key': 'SnapDeleteOn',
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
