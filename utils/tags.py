import getpass  # library for sensitive user input

def get_standard_tags(): # getpass.getuser() gets the current shell username

    try:
        owner = getpass.getuser()
    except Exception:
        owner = "unknown"

    return {
        'CreatedBy': 'molcho-platform-cli',
        'Owner': owner,
        'Project': 'python-integrative-exercise'
    }


def format_as_ec2_tags(resource_type): # Converts a dict to a list of dicts that boto3.ec2 requires

    tags_dict = get_standard_tags()

    ec2_tags = [{'Key': k, 'Value': v} for k, v in tags_dict.items()]

    return [{
        'ResourceType': resource_type,
        'Tags': ec2_tags
    }]
