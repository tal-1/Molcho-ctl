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
            # Get the region from the current session
            session = boto3.session.Session()
            current_region = session.region_name
            
            # --- FIX: Handle case where region is None ---
            if current_region is None:
                current_region = 'us-east-1'
            # ---------------------------------------------
            
            # 1. Create Bucket
            if current_region == 'us-east-1':
                self.s3.create_bucket(Bucket=bucket_name)
            else:
                self.s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': current_region}
                )
            
            # ... rest of the function remains the same ...

            # 2. Apply Tags
            # We use the existing helper to generate the list of tags
            # format_as_ec2_tags returns {'ResourceType':..., 'Tags': [...]}
            # We just need the list inside 'Tags'
            tag_data = format_as_ec2_tags('s3')
            tags_list = tag_data['Tags']
            
            self.s3.put_bucket_tagging(
                Bucket=bucket_name,
                Tagging={'TagSet': tags_list}
            )

            # 3. Configure Security (Public vs Private)
            if public:
                # If public, we turn OFF the "Block Public Access" settings
                self.s3.delete_public_access_block(Bucket=bucket_name)
            else:
                # Block all public access (Secure default)
                self.s3.put_public_access_block(
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
