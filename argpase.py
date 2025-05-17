import argparse
import boto3
import ipaddress
import sys


def validate_cidr(cidr: str) -> str:
    
    try:
        ipaddress.IPv4Network(cidr)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid CIDR: {cidr}")
    return cidr


def create_vpc(ec2, cidr_block: str, name: str) -> str:
    vpc = ec2.create_vpc(CidrBlock=cidr_block)
    vpc.wait_until_available()
    vpc.create_tags(Tags=[{"Key": "Name", "Value": name}])
    print(f"✅ Created VPC: {vpc.id}")
    return vpc.id


def create_internet_gateway(ec2, vpc_id: str) -> str:
    igw = ec2.create_internet_gateway()
    igw.attach_to_vpc(VpcId=vpc_id)
    print(f"✅ Created and attached Internet Gateway: {igw.id}")
    return igw.id


def create_subnet(ec2, vpc_id: str, cidr_block: str, name: str, az: str) -> str:
    subnet = ec2.create_subnet(VpcId=vpc_id, CidrBlock=cidr_block, AvailabilityZone=az)
    subnet.create_tags(Tags=[{"Key": "Name", "Value": name}])
    print(f"✅ Created Subnet: {subnet.id} ({name})")
    return subnet.id


def create_route_table(ec2, vpc_id: str, subnet_id: str, igw_id: str | None, name: str):
    table = ec2.create_route_table(VpcId=vpc_id)
    table.create_tags(Tags=[{"Key": "Name", "Value": name}])
    table.associate_with_subnet(SubnetId=subnet_id)

    if igw_id:
        table.create_route(DestinationCidrBlock="0.0.0.0/0", GatewayId=igw_id)
        print(f"✅ Public Route added to IGW in {name}")
    else:
        print(f"✅ Created private Route Table: {table.id}")

    return table.id


def main():
    parser = argparse.ArgumentParser(description="Create VPC with subnets and routing")

    parser.add_argument("--vpc-cidr", type=validate_cidr, required=True, help="VPC CIDR block")
    parser.add_argument("--vpc-name", required=True, help="VPC name tag")

    parser.add_argument("--public-subnet-cidr", type=validate_cidr, required=True, help="Public Subnet CIDR")
    parser.add_argument("--private-subnet-cidr", type=validate_cidr, required=True, help="Private Subnet CIDR")

    parser.add_argument("--availability-zone", required=True, help="Availability Zone, e.g., us-east-1a")

    args = parser.parse_args()

    ec2 = boto3.resource("ec2")

    try:
        vpc_id = create_vpc(ec2, args.vpc_cidr, args.vpc_name)
        igw_id = create_internet_gateway(ec2, vpc_id)

        public_subnet_id = create_subnet(ec2, vpc_id, args.public_subnet_cidr, "PublicSubnet", args.availability_zone)
        private_subnet_id = create_subnet(ec2, vpc_id, args.private_subnet_cidr, "PrivateSubnet", args.availability_zone)

        create_route_table(ec2, vpc_id, public_subnet_id, igw_id, "PublicRouteTable")
        create_route_table(ec2, vpc_id, private_subnet_id, None, "PrivateRouteTable")

        print("🎉 All resources created successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
