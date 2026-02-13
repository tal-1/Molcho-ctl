import boto3
import time
from botocore.exceptions import ClientError

class Route53Manager:
    def __init__(self):
        self.client = boto3.client('route53')
        self.signature = 'Created by Molcho Platform CLI'

    # --- PART 1: Zone Management (Domains) ---

    def create_hosted_zone(self, domain_name, private_zone=False):
        """Create a new Route53 Hosted Zone."""
        try:
            ref = f"molcho-cli-{int(time.time())}"
            config = {
                'Comment': self.signature, 
                'PrivateZone': private_zone
            }
            
            response = self.client.create_hosted_zone(
                Name=domain_name,
                CallerReference=ref,
                HostedZoneConfig=config
            )
            return {
                "id": response['HostedZone']['Id'], 
                "name": response['HostedZone']['Name']
            }
        except ClientError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": str(e)}

    # ALIAS: This allows the CLI to call 'create_zone' while the GUI calls 'create_hosted_zone'
    def create_zone(self, domain_name, private_zone=False):
        return self.create_hosted_zone(domain_name, private_zone)

    def list_hosted_zones(self):
        """List ONLY hosted zones created by this tool."""
        try:
            response = self.client.list_hosted_zones()
            my_zones = []
            
            for z in response['HostedZones']:
                comment = z.get('Config', {}).get('Comment', '')
                if comment == self.signature:
                    my_zones.append({
                        "Id": z['Id'],
                        "Name": z['Name'],
                        "Count": z['ResourceRecordSetCount'],
                        "Private": z['Config']['PrivateZone']
                    })
            return my_zones
        except ClientError as e:
            print(f"AWS Error: {e}")
            return []
        except Exception as e:
            print(f"Error: {e}")
            return []

    # --- PART 2: Record Management (DNS Records) ---

    def create_record(self, zone_id, record_name, record_type, record_value, ttl=300):
        """Create a DNS record (A, CNAME, TXT, etc)."""
        try:
            self.client.change_resource_record_sets(
                HostedZoneId=zone_id,
                ChangeBatch={
                    'Comment': self.signature,
                    'Changes': [{
                        'Action': 'UPSERT',
                        'ResourceRecordSet': {
                            'Name': record_name,
                            'Type': record_type,
                            'TTL': int(ttl),
                            'ResourceRecords': [{'Value': record_value}]
                        }
                    }]
                }
            )
            return {"success": True}
        except ClientError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": str(e)}

    def delete_record(self, zone_id, record_name, record_type, record_value):
        """Delete a specific DNS record."""
        try:
            self.client.change_resource_record_sets(
                HostedZoneId=zone_id,
                ChangeBatch={
                    'Changes': [{
                        'Action': 'DELETE',
                        'ResourceRecordSet': {
                            'Name': record_name,
                            'Type': record_type,
                            'TTL': 300,
                            'ResourceRecords': [{'Value': record_value}]
                        }
                    }]
                }
            )
            return {"success": True}
        except ClientError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": str(e)}

    def list_records(self, zone_id):
        """List all DNS records in a specific hosted zone."""
        try:
            response = self.client.list_resource_record_sets(HostedZoneId=zone_id)
            
            clean_records = []
            for r in response['ResourceRecordSets']:
                if 'ResourceRecords' in r and len(r['ResourceRecords']) > 0:
                    value = r['ResourceRecords'][0]['Value']
                else:
                    value = "Alias/Complex"

                clean_records.append({
                    "Name": r['Name'],
                    "Type": r['Type'],
                    "TTL": r.get('TTL', '-'),
                    "Value": value
                })
            return clean_records
        except ClientError as e:
            print(f"AWS Error listing records: {e}")
            return []
        except Exception as e:
            print(f"Error listing records: {e}")
            return []
