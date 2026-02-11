#!/usr/bin/env python3

import click
from rich.console import Console
from rich.table import Table

from resources.ec2_manager import EC2Manager
from resources.s3_manager import S3Manager
from resources.route53_manager import Route53Manager

# Initialize Rich Console
console = Console()

# --- 1. Define the "Bottom Section" (Examples & Syntax) ---
EXAMPLES = """
----------------------------------------------------------------------------------------
EC2 (Server Management)

  Commands:
    create, list, start, stop, delete

  Arguments:
    --name <name_of_instance>   Name tag for the server
    --os <ubuntu|amazon_linux>  Operating System choice
    --type <t3.micro|t2.small>  Instance Size
    --id <instance_id>          Target Instance ID (Required for start/stop/delete)

  Examples:
    molchoctl ec2 create --name web-01 --os amazon_linux --type t3.micro
    molchoctl ec2 list
    molchoctl ec2 stop --id i-0123456789abcdef0
    molchoctl ec2 start --id i-0123456789abcdef0
    molchoctl ec2 delete --id i-0123456789abcdef0

----------------------------------------------------------------------------------------
S3 (Object Storage)

  Commands:
    create, list, delete, upload

  Arguments:
    --name <bucket_name>      Globally Unique Name of the bucket (for create/delete)
    --public                  Flag: If present, makes the bucket Public (Read-Only)
    --bucket <bucket_name>    Target bucket (for upload)
    --file <file_path>        Path to the file
    --yes                     Flag: Confirm deletion automatically (skip prompt)

  Examples:
    molchoctl s3 create --name example-secure-bucket
    molchoctl s3 create --name example-public-bucket --public
    molchoctl s3 list
    molchoctl s3 upload --bucket example-secure-bucket --file ./index.html
    molchoctl s3 delete --name example-secure-bucket
    molchoctl s3 delete --name example-public-bucket --yes

----------------------------------------------------------------------------------------
Route53 (DNS Management)

  Commands:
    create-zone, list-zones, create

  Arguments:
    --name <domain_name>      Name of Zone or Record
    --zone <zone_id>          The Hosted Zone ID (Get this from list-zones)
    --ip <ip_address>         The Target IP Address for the record

  Examples:
    molchoctl route53 create-zone --name example-zone.com
    molchoctl route53 list-zones
    molchoctl route53 create --zone Z0123456789 --name web.example-zone.com --ip 1.2.3.4
"""

# --- 2. Define the Custom Class (The Pager Logic) ---
class PagedGroup(click.Group):
    """
    This class forces the help output to open in a 'Pager' (like the 'less' command).
    It also handles invalid commands gracefully.
    """
    def get_help(self, ctx):
        # Generate the standard help text
        help_text = super().get_help(ctx)
        # Send it to the pager (user presses 'q' to exit)
        click.echo_via_pager(help_text)
        # Exit the program immediately so Click doesn't try to print the text again
        ctx.exit()

    def format_help(self, ctx, formatter):
        """
        Overriding this method allows us to change the ORDER of the output.
        """
        # 1. Print Welcome Message (Flush Left, No Indent)
        # We access the docstring directly to avoid Click's auto-indentation
        formatter.write(self.help + "\n\n")

        # 2. Print Usage
        self.format_usage(ctx, formatter)
        
        # 3. Print Options/Commands (Standard Click Formatting)
        self.format_options(ctx, formatter)
        
        # 4. Print the Cheat Sheet (Raw, preserving our spacing)
        if self.epilog:
            formatter.write("\n" + self.epilog + "\n")


    def resolve_command(self, ctx, args):
        try:
            return super().resolve_command(ctx, args)
        except click.exceptions.UsageError as e:
            # Custom Error Message for Invalid Commands
            console.print(f"[bold red]Error:[/bold red] {e.message}")
            console.print("[yellow]Try 'molchoctl --help' or 'molchoctl -h' for more information.[/yellow]")
            ctx.exit()

# --- 3. The Main CLI Setup ---
@click.group(
    cls=PagedGroup,  # Use our custom Pager class
    context_settings={'help_option_names': ['-h', '--help']}, # Enable -h
    epilog=EXAMPLES  # Add the examples to the bottom
)
@click.version_option(version='1.0.0', prog_name='molchoctl')
def cli():
    """ ██████   ██████          ████           █████                                    █████    ████ 
▒▒██████ ██████          ▒▒███          ▒▒███                                    ▒▒███    ▒▒███ 
 ▒███▒█████▒███   ██████  ▒███   ██████  ▒███████    ██████              ██████  ███████   ▒███ 
 ▒███▒▒███ ▒███  ███▒▒███ ▒███  ███▒▒███ ▒███▒▒███  ███▒▒███ ██████████ ███▒▒███▒▒▒███▒    ▒███ 
 ▒███ ▒▒▒  ▒███ ▒███ ▒███ ▒███ ▒███ ▒▒▒  ▒███ ▒███ ▒███ ▒███▒▒▒▒▒▒▒▒▒▒ ▒███ ▒▒▒   ▒███     ▒███ 
 ▒███      ▒███ ▒███ ▒███ ▒███ ▒███  ███ ▒███ ▒███ ▒███ ▒███           ▒███  ███  ▒███ ███ ▒███ 
 █████     █████▒▒██████  █████▒▒██████  ████ █████▒▒██████            ▒▒██████   ▒▒█████  █████
▒▒▒▒▒     ▒▒▒▒▒  ▒▒▒▒▒▒  ▒▒▒▒▒  ▒▒▒▒▒▒  ▒▒▒▒ ▒▒▒▒▒  ▒▒▒▒▒▒              ▒▒▒▒▒▒     ▒▒▒▒▒  ▒▒▒▒▒ 
                                                                                                
                                                                                                
                                                                                                

Welcome to the Molcho Platform Engineering CLI!

Manage AWS resources (EC2, S3, Route53) safely.
"""
    pass

# EC2 Management Group

@cli.group()
def ec2():
    """Manage EC2 Instances (Create, List, Start, Stop, Delete)"""
    pass

@ec2.command()
@click.option('--type', 'instance_type', default='t3.micro', type=click.Choice(['t3.micro', 't2.small']), help='Instance Type')
@click.option('--os', 'os_type', type=click.Choice(['amazon_linux', 'ubuntu']), default='amazon_linux', help='OS Choice')
@click.option('--name', required=True, help='Name tag for the server')
def create(instance_type, os_type, name):
    """Provision a new EC2 instance."""
    manager = EC2Manager()
    
    console.print(f"[bold blue]Provisioning {os_type} instance ({instance_type})...[/bold blue]")
    
    # Run the logic
    result = manager.create_instance(instance_type, name, os_type)
    
    if "error" in result:
        console.print(f"[bold red]FAILED:[/bold red] {result['error']}")
        return
    else:
        console.print(f"[bold green]SUCCESS:[/bold green] Created instance [bold]{result['id']}[/bold]")

@ec2.command("list")
def list_instances():
    """List all instances created by this tool."""
    manager = EC2Manager()
    instances = manager.list_instances()

    if not instances:
        console.print("[yellow]No instances found with tag 'CreatedBy=molcho-platform-cli'[/yellow]")
        return

    # Creates a pretty table
    table = Table(title="My Platform Instances")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Type")
    table.add_column("State")
    table.add_column("Public IP", style="green")

    for i in instances:
        # Color code the state
        state_style = "green" if i['State'] == 'running' else "red"
        
        table.add_row(
            i['ID'],
            i['Name'],
            i['Type'],
            f"[{state_style}]{i['State']}[/{state_style}]",
            i['PublicIP']
        )

    console.print(table)

@ec2.command()
@click.option('--id', 'instance_id', required=True, help='Instance ID (i-xxxx)')
def start(instance_id):
    """Start a stopped instance."""
    manager = EC2Manager()
    console.print(f"Starting {instance_id}...")
    result = manager.manage_state(instance_id, 'start')
    
    if "error" in result:
        console.print(f"[red]Error:[/red] {result['error']}")
    else:
        console.print(f"[green]Signal sent to start {instance_id}[/green]")

@ec2.command()
@click.option('--id', 'instance_id', required=True, help='Instance ID (i-xxxx)')
def stop(instance_id):
    """Stop a running instance."""
    manager = EC2Manager()
    console.print(f"Stopping {instance_id}...")
    result = manager.manage_state(instance_id, 'stop')
    
    if "error" in result:
        console.print(f"[red]Error:[/red] {result['error']}")
    else:
        console.print(f"[green]Signal sent to stop {instance_id}[/green]")

@ec2.command()
@click.option('--id', 'instance_id', required=True, help='Instance ID (i-xxxx)')
@click.confirmation_option(prompt='Are you sure you want to PERMANENTLY delete this server?')
def delete(instance_id):
    """Terminate (delete) an instance."""
    manager = EC2Manager()
    console.print(f"[bold red]Terminating {instance_id}...[/bold red]")
    result = manager.manage_state(instance_id, 'delete')
    
    if "error" in result:
        console.print(f"[red]Error:[/red] {result['error']}")
    else:
        console.print(f"[green]Instance {instance_id} terminated.[/green]")

@ec2.command()
@click.option('--id', 'instance_id', required=True, help='Instance ID (i-xxxx)')
@click.option('--type', 'new_type', required=True, help='New Instance Type (e.g. t2.small)')
def update(instance_id, new_type):
    """Update instance type (Resize). Instance must be stopped."""
    manager = EC2Manager()
    console.print(f"Resizing {instance_id} to {new_type}...")
    result = manager.update_instance(instance_id, new_type)
    
    if "error" in result:
        console.print(f"[red]Error:[/red] {result['error']}")
    else:
        console.print(f"[green]Success! Instance resized.[/green]")

# S3 Management Group

@cli.group()
def s3():
    """Manage S3 Buckets (Create, List, Delete)"""
    pass

@s3.command()
@click.option('--name', required=True, help='Bucket Name (Must be globally unique)')
@click.option('--public', is_flag=True, help='Make bucket PUBLIC (Dangerous!)')
def create(name, public):
    """Create a new S3 bucket (Private by default)."""
    manager = S3Manager()
    
    # 1. Safety Check for Public Buckets
    if public:
        console.print(f"[bold red]WARNING: You are about to make bucket '{name}' PUBLIC![/bold red]")
        # This triggers the "Are you sure? [y/N]" prompt automatically.
        # If user types 'n', the program stops here (abort=True).
        click.confirm('Are you sure you want to proceed?', abort=True)

    console.print(f"[bold blue]Creating bucket {name}...[/bold blue]")
    
    # 2. Run Logic
    result = manager.create_bucket(name, public)
    
    if "error" in result:
        console.print(f"[bold red]FAILED:[/bold red] {result['error']}")
    else:
        status_color = "red" if public else "green"
        console.print(f"[bold green]SUCCESS:[/bold green] Bucket created.")
        console.print(f"Status: [bold {status_color}]{result['status']}[/bold {status_color}]")

@s3.command("list")
def list_buckets():
    """List buckets created by this tool."""
    manager = S3Manager()
    buckets = manager.list_buckets()

    if not buckets:
        console.print("[yellow]No managed buckets found.[/yellow]")
        return

    table = Table(title="My S3 Buckets")
    table.add_column("Name", style="cyan")
    table.add_column("Created At", style="magenta")

    for b in buckets:
        table.add_row(b['Name'], b['CreationDate'])

    console.print(table)

@s3.command()
@click.option('--name', required=True, help='Bucket Name')
@click.confirmation_option(prompt='Are you sure you want to PERMANENTLY delete this bucket?')
def delete(name):
    """Delete an S3 bucket (Must be empty)."""
    manager = S3Manager()
    console.print(f"[bold red]Deleting bucket {name}...[/bold red]")
    
    result = manager.delete_bucket(name)
    
    if "error" in result:
        console.print(f"[bold red]Error:[/bold red] {result['error']}")
    else:
        console.print(f"[bold green]Bucket {name} deleted.[/bold green]")


@s3.command()
@click.option('--bucket', required=True, help='Target Bucket Name')
@click.option('--file', 'file_path', required=True, help='Path to file on your computer')
def upload(bucket, file_path):
    """Securely upload a file to a managed bucket."""
    manager = S3Manager()
    console.print(f"Uploading [bold]{file_path}[/bold] to [bold]{bucket}[/bold]...")
    
    result = manager.upload_file(bucket, file_path)
    
    if "error" in result:
        console.print(f"[bold red]FAILED:[/bold red] {result['error']}")
    else:
        console.print(f"[bold green]SUCCESS:[/bold green] File uploaded successfully.")

# Route53 Management Group

@cli.group()
def route53():
    """Manage DNS Records."""
    pass

@route53.command("list-zones")
def list_zones():
    """List available Hosted Zones."""
    manager = Route53Manager()
    zones = manager.list_hosted_zones()

    if not zones:
        console.print("[yellow]No Hosted Zones found.[/yellow]")
        return

    table = Table(title="Available DNS Zones")
    table.add_column("Zone ID", style="cyan")
    table.add_column("Domain Name", style="green")

    for z in zones:
        table.add_row(z['Id'].split('/')[-1], z['Name'])

    console.print(table)

@route53.command("create-zone")
@click.option('--name', required=True, help='Domain Name (Must start with molcho-)')
def create_zone_cmd(name):
    """Create a new Hosted Zone (DNS Domain)."""
    manager = Route53Manager()
    console.print(f"[bold blue]Creating Hosted Zone {name}...[/bold blue]")
    
    result = manager.create_zone(name)
    
    if "error" in result:
        console.print(f"[bold red]FAILED:[/bold red] {result['error']}")
    else:
        console.print(f"[bold green]SUCCESS:[/bold green] Zone created.")
        console.print(f"Zone ID: [cyan]{result['id']}[/cyan]")

@route53.command()
@click.option('--zone', required=True, help='Hosted Zone ID (Get this from list-zones)')
@click.option('--name', required=True, help='Full Record Name (e.g., molcho-web.somedomain.com)')
@click.option('--ip', required=True, help='Target IP Address')
def create(zone, name, ip):
    """Create a DNS Record (A Record)."""
    manager = Route53Manager()
    console.print(f"[bold blue]Pointing {name} -> {ip}...[/bold blue]")
    
    result = manager.create_record(zone, name, ip)
    
    if "error" in result:
        console.print(f"[bold red]FAILED:[/bold red] {result['error']}")
    else:
        console.print(f"[bold green]SUCCESS:[/bold green] DNS Record created/updated.")

if __name__ == '__main__':
    cli()
