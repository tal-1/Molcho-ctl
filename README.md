# The Molcho-ctl Platform

A self-service tool for managing AWS resources via CLI and Web Dashboard.

This tool automates the provisioning of EC2 instances, S3 buckets and Route53 DNS zones, while enforcing strict safety guardrails and tagging standards.

## 🚀 **Features**

* **EC2:** Launch safe, pre-configured instances (`t3.micro` or `t2.small` only) with a hard cap of 2 active instances.
* **S3:** Create standard storage buckets with mandatory public access confirmation.
* **Route53:** Manage internal DNS hosted zones and records.
* **Safety & Compliance:** All resources are automatically tagged and filtered so the tool only manages its own resources.


## 🏷️ T**agging Strategy**
To ensure safety and ownership, all resources created by this tool are automatically tagged with:

* **Project:** python-integrative-exercise
* **Owner:** <your-username> (Detected automatically)
* **CreatedBy:** molcho-platform-cli

Note: The tool strictly filters list views to show only resources containing the CreatedBy tag or signature.


## 🛠️ I**nstallation**

1.  **Prerequisites:**
    * Python 3.10+
    * AWS CLI configured with active credentials (using the `aws configure` command)

2.  **Setup:**
    ```bash
    git clone https://github.com/tal-1/Molcho-ctl.git
    cd Molcho-ctl
    
    # Create a virtual environment if you already have python on your machine (optional but recommended)
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    
    # Install dependencies
    pip install -r requirements.txt
    pip install --editable .
    ```



## 💻 **CLI Usage**
You can manage resources directly from your terminal using the `molchoctl` command.

For more information use the command `molchoctl -h`


### **EC2 (Compute):**
#### List all instances created by this tool
* `molchoctl ec2 list`

#### Create a new web server (Safe types only)
* `molchoctl ec2 create --name web-server-1 --type t3.micro`

#### Stop an instance
* `molchoctl ec2 stop --id i-0123456789abcdef0`

##

### **S3 (Storage):**
#### Create a private bucket
* `molchoctl s3 create --name my-data-bucket --private`

#### Create a public bucket (Requires confirmation)
* `molchoctl s3 create --name my-public-assets --public`

##

### **Route53 (DNS):**
#### List hosted zones
* `molchoctl route53 list-zones`

#### Create a new zone
* `molchoctl route53 create-zone --domain molcho-app.internal`
##

## 💻 **Web GUI Usage**
For a visual interface, launch the Streamlit dashboard:

`streamlit run app.py`

This will open a local website at http://localhost:8501 where you can manage all resources via a GUI.
