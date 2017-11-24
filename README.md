change 1
# create ebs snapshot lambda on time trigger 
	create-ebs.py
#copy ebs snapshot to standby region on time trigger
	copy-ebs.py
#create snapshot from existing volume on event(Instance Create, Terminate etc), delete the volume after instance is detached
	sns-trigger.py
#delete snapshot on regular intervals on depending the tag date
	delete-ebs.py
added log extract
no more changes

Test
