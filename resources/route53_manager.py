import boto3
import time
from botocore.exceptions import ClientError

class Route53Manager:
    def __init__(self):
        self.client = boto3.client('route53')
        # This comment acts as a "Signature" to prove we created the zone
        self.MARKER = 'Created by Molcho Platform CLI'

    def create_zone(self, zone_name):
        """Create a new Route53 Hosted Zone."""
        try:
            ref = f"{zone_name}-{int(time.time())}"
            response = self.client.create_hosted_zone(
                Name=zone_name,
                CallerReference=ref,
                HostedZoneConfig={'Comment': self.MARKER}
            )
            return {
                "success": True, 
                "id": response['HostedZone']['Id'], 
                "name": response['HostedZone']['Name']
            }
        except ClientError as e:
            return {"error": str(e)}

    def list_hosted_zones(self):
        """List ONLY zones created by this CLI."""
        try:
            response = self.client.list_hosted_zones()
            my_zones = []
            
            for z in response['HostedZones']:
                # Filter: Only show zones with our specific comment
                if z.get('Config', {}).get('Comment') == self.MARKER:
                    my_zones.append({
                        'Id': z['Id'],
                        'Name': z['Name'],
                        'Count': z['ResourceRecordSetCount']
                    })
            return my_zones
        except ClientError as e:
            return []

    def create_record(self, zone_id, record_name, target_ip):
        """Create an A-Record (Only if we own the Zone)."""
        
        # 1. Ownership Check
        try:
            zone_info = self.client.get_hosted_zone(Id=zone_id)
            comment = zone_info['HostedZone'].get('Config', {}).get('Comment', '')
            if comment != self.MARKER:
                return {"error": "ACCESS DENIED: You can only manage records for zones created by this CLI."}
        except ClientError as e:
            return {"error": f"Zone not found: {str(e)}"}

        # 2. Create Record
        try:
            self.client.change_resource_record_sets(
                HostedZoneId=zone_id,
                ChangeBatch={
                    'Comment': 'Created by Molcho Platform CLI',
                    'Changes': [{
                        'Action': 'UPSERT',
                        'ResourceRecordSet': {
                            'Name': record_name,
                            'Type': 'A',
                            'TTL': 300,
                            'ResourceRecords': [{'Value': target_ip}]
                        }
                    }]
                }
            )
            return {"success": True}
        except ClientError as e:
            return {"error": str(e)}
