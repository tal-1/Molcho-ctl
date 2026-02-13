import boto3
from botocore.exceptions import ClientError
# We import the generic tag function since the structure (List of Dicts) is compatible
from utils.tags import format_as_ec2_tags

class S3Manager:
    def __init__(self, region='us-east-1'):
        # We consistently use 'self.s3' everywhere now
        self.s3 = boto3.client('s3', region_name=region)
        self.region = region

    def create_bucket(self, bucket_name, public=False):
        """
        Create an S3 bucket with tags and specific access settings.
        Handles Region LocationConstraint automatically.
        """
        try:
            # 1. Detect the correct region from your AWS Config
            session = boto3.session.Session()
            current_region = session.region_name
            
            # If no region is configured, default to N. Virginia
            if current_region is None:
                current_region = 'us-east-1'

            # 2. Create a FRESH client specifically for this region
            # This bypasses any "background" defaults the server might force on self.s3
            s3_client = boto3.client('s3', region_name=current_region)

            # 3. Create Bucket with correct logic
            if current_region == 'us-east-1':
                # Case A: N. Virginia (Global Endpoint)
                s3_client.create_bucket(Bucket=bucket_name)
            else:
                # Case B: All other regions (Require Constraint)
                s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': current_region}
                )

            # 4. Apply Tags (Ownership) using the new client
            from utils.tags import format_as_ec2_tags
            tag_data = format_as_ec2_tags('s3')
            tags_list = tag_data['Tags']
            
            s3_client.put_bucket_tagging(
                Bucket=bucket_name,
                Tagging={'TagSet': tags_list}
            )

            # 5. Configure Security (Public vs Private) using the new client
            if public:
                s3_client.delete_public_access_block(Bucket=bucket_name)
            else:
                s3_client.put_public_access_block(
                    Bucket=bucket_name,
                    PublicAccessBlockConfiguration={
                        'BlockPublicAcls': True,
                        'IgnorePublicAcls': True,
                        'BlockPublicPolicy': True,
                        'RestrictPublicBuckets': True
                    }
                )

            return {"success": True, "name": bucket_name, "status": "created"}

        except ClientError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": str(e)}

    def list_buckets(self):
        """List only buckets created by this CLI (checked via Tags)."""
        try:
            response = self.s3.list_buckets()
            my_buckets = []

            print("Scanning buckets for tags (this might take a moment)...")
            
            for bucket in response['Buckets']:
                name = bucket['Name']
                
                try:
                    # Check tags
                    tags = self.s3.get_bucket_tagging(Bucket=name)
                    tag_list = tags.get('TagSet', [])
                    
                    # Look for our signature tag
                    is_ours = False
                    for t in tag_list:
                        if t['Key'] == 'CreatedBy' and t['Value'] == 'molcho-platform-cli':
                            is_ours = True
                            break
                    
                    if is_ours:
                        my_buckets.append({
                            'Name': name,
                            'CreationDate': bucket['CreationDate'].strftime("%Y-%m-%d %H:%M")
                        })
                        
                except ClientError:
                    continue

            return my_buckets
        except ClientError as e:
            return []

    def delete_bucket(self, bucket_name):
        """Delete a bucket (must be empty and owned by CLI)."""
        try:
            # 1. Verify Ownership (Safety Check)
            try:
                tags = self.s3.get_bucket_tagging(Bucket=bucket_name)
                tag_list = tags.get('TagSet', [])
                
                is_ours = False
                for t in tag_list:
                    if t['Key'] == 'CreatedBy' and t['Value'] == 'molcho-platform-cli':
                        is_ours = True
                        break
                
                if not is_ours:
                    return {"error": "Access Denied: You can only delete buckets created by this CLI."}
            
            except ClientError:
                pass

            # 2. Perform Delete
            self.s3.delete_bucket(Bucket=bucket_name)
            return {"success": True}

        except ClientError as e:
            if "BucketNotEmpty" in str(e):
                return {"error": "Bucket is not empty. Please empty it first."}
            return {"error": str(e)}

    def upload_file(self, bucket_name, file_path, object_name=None):
        """Upload a file to an S3 bucket."""
        try:
            # 1. Verify Ownership
            tags = self.s3.get_bucket_tagging(Bucket=bucket_name)
            tag_list = tags.get('TagSet', [])
            
            is_ours = False
            for t in tag_list:
                if t['Key'] == 'CreatedBy' and t['Value'] == 'molcho-platform-cli':
                    is_ours = True
                    break
            
            if not is_ours:
                return {"error": "Access Denied: This bucket was not created by this CLI."}

            # 2. Upload
            if object_name is None:
                object_name = file_path

            self.s3.upload_file(file_path, bucket_name, object_name)
            return {"success": True, "file": object_name}

        except ClientError as e:
            return {"error": str(e)}
        except FileNotFoundError:
            return {"error": f"The file '{file_path}' was not found."}
