import boto3
from botocore.exceptions import ClientError
from utils.tags import format_as_ec2_tags

class EC2Manager:
    def __init__(self, region='us-east-1'):
        self.ec2 = boto3.client('ec2', region_name=region)
        self.ssm = boto3.client('ssm', region_name=region)
        # TAG FILTER: Matches your username from utils/tags.py
        self.TAG_FILTER = {'Name': 'tag:CreatedBy', 'Values': ['molcho-platform-cli']}

    def _get_latest_ami(self, os_type):
        """
        Fetches the latest AMI ID dynamically from AWS SSM Public Parameters.
        """
        # Map user choice to the official AWS SSM Parameter path
        ssm_paths = {
            'amazon_linux': '/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64',
            'ubuntu': '/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id'
        }
        
        # Default to Amazon Linux if something goes wrong with the key
        path = ssm_paths.get(os_type, ssm_paths['amazon_linux'])

        try:
            response = self.ssm.get_parameter(Name=path, WithDecryption=False)
            return response['Parameter']['Value']
        except ClientError as e:
            print(f"Error fetching AMI for {os_type}: {e}")
            # Fallback hardcoded IDs (us-east-1) in case SSM fails
            if os_type == 'ubuntu':
                return "ami-0c7217cdde317cfec" # Ubuntu 22.04
            return "ami-04b70fa74e45c3917"    # AL2023

    def list_instances(self):
        """List only instances created by this CLI."""
        try:
            response = self.ec2.describe_instances(Filters=[self.TAG_FILTER])
            instances = []
            for reservation in response['Reservations']:
                for inst in reservation['Instances']:
                    name = "N/A"
                    if 'Tags' in inst:
                        for t in inst['Tags']:
                            if t['Key'] == 'Name':
                                name = t['Value']
                    
                    instances.append({
                        'ID': inst['InstanceId'],
                        'State': inst['State']['Name'],
                        'Type': inst['InstanceType'],
                        'Name': name,
                        'PublicIP': inst.get('PublicIpAddress', 'N/A')
                    })
            return instances
        except ClientError as e:
            print(f"Debug: {e}")
            return []

    def create_instance(self, instance_type, name_tag, os_type):
        """
        Create instance. 
        Args:
            instance_type (str): t2.small or t3.micro
            name_tag (str): Name of the server
            os_type (str): 'amazon_linux' or 'ubuntu'
        """
        
        # 1. Enforce Hard Cap
        current_instances = self.list_instances()
        active_count = sum(1 for i in current_instances if i['State'] != 'terminated')
        
        if active_count >= 2:
            return {"error": f"POLICY VIOLATION: Limit reached ({active_count}/2 instances)."}

        # 2. Enforce Instance Type
        allowed_types = ['t2.small', 't3.micro']
        if instance_type not in allowed_types:
            return {"error": f"POLICY VIOLATION: Type '{instance_type}' not allowed. Allowed: {allowed_types}"}

        # 3. Create
        try:
            print(f"Fetching latest AMI for {os_type}...")
            # FIX WAS HERE: We now explicitly pass 'os_type' to the helper function
            ami_id = self._get_latest_ami(os_type)
            
            tag_spec = format_as_ec2_tags('instance')
            tag_spec[0]['Tags'].append({'Key': 'Name', 'Value': name_tag})

            response = self.ec2.run_instances(
                ImageId=ami_id,
                InstanceType=instance_type,
                MinCount=1,
                MaxCount=1,
                TagSpecifications=tag_spec
            )
            return {"success": True, "id": response['Instances'][0]['InstanceId']}
            
        except ClientError as e:
            return {"error": str(e)}

    def manage_state(self, instance_id, action):
        """Start, Stop, or Terminate (Delete) an instance."""
        try:
            # Check ownership
            check = self.ec2.describe_instances(
                InstanceIds=[instance_id],
                Filters=[self.TAG_FILTER]
            )
            if not check['Reservations']:
                return {"error": "Access Denied: Not a CLI-created instance."}

            if action == 'start':
                self.ec2.start_instances(InstanceIds=[instance_id])
            elif action == 'stop':
                self.ec2.stop_instances(InstanceIds=[instance_id])
            elif action == 'delete':
                self.ec2.terminate_instances(InstanceIds=[instance_id])
            
            return {"success": True}
        except ClientError as e:
            return {"error": str(e)}

    def update_instance(self, instance_id, new_type):
        """Resize instance (Must be stopped)."""
        try:
            check = self.ec2.describe_instances(InstanceIds=[instance_id], Filters=[self.TAG_FILTER])
            if not check['Reservations']:
                return {"error": "Access Denied."}

            state = check['Reservations'][0]['Instances'][0]['State']['Name']
            if state != 'stopped':
                return {"error": f"Cannot update running instance. Please STOP {instance_id} first."}

            allowed_types = ['t2.small', 't3.micro']
            if new_type not in allowed_types:
                return {"error": f"Type '{new_type}' not allowed."}

            self.ec2.modify_instance_attribute(
                InstanceId=instance_id,
                InstanceType={'Value': new_type}
            )
            return {"success": True}
        except ClientError as e:
            return {"error": str(e)}

    def _get_latest_ami(self, os_type):
        """
        Helper: Fetches the latest AMI ID from AWS Systems Manager (SSM) Parameter Store.
        This ensures we always launch the most secure, up-to-date version of the OS.
        """
        # Map our user-friendly names to AWS SSM Parameter paths
        ami_map = {
            'amazon_linux': '/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64',
            'ubuntu': '/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id'
        }

        if os_type not in ami_map:
            raise ValueError(f"Unknown OS type: {os_type}")

        try:
            # We create a temporary client just for SSM
            # (Make sure 'import boto3' is at the top of your file!)
            ssm_client = boto3.client('ssm')
            
            # Fetch the parameter
            response = ssm_client.get_parameter(Name=ami_map[os_type])
            
            # Extract the actual AMI ID (e.g., "ami-012345...")
            return response['Parameter']['Value']

        except ClientError as e:
            # If SSM fails, we raise an error so create_instance can catch it
            raise Exception(f"Failed to fetch dynamic AMI: {str(e)}")
