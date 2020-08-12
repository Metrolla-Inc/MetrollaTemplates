from troposphere import Base64, FindInMap, GetAtt
from troposphere import GetAtt, Join, Output, Parameter, Ref, Template
from troposphere.s3 import Bucket, AuthenticatedRead
import troposphere.ec2 as ec2
from troposphere.ec2 import SecurityGroup
from troposphere.rds import DBInstance, DBSubnetGroup


t = Template()

keyname_param = t.add_parameter(Parameter(
    "KeyName",
    Description="Name of an existing EC2 KeyPair to enable SSH "
                "access to the instance",
    Type="String",
))

vpcid = t.add_parameter(Parameter(
    "VpcId",
    Type="String",
    Description="VpcId of your existing Virtual Private Cloud (VPC)"
))

subnet = t.add_parameter(Parameter(
    "Subnets",
    Type="CommaDelimitedList",
    Description=(
        "The list of SubnetIds, for at least two Availability Zones in the "
        "region in your Virtual Private Cloud (VPC)")
))

t.add_mapping('RegionMap', {
    "us-east-1": {"AMI": "ami-7f418316"},
    "us-west-1": {"AMI": "ami-951945d0"},
    "us-west-2": {"AMI": "ami-16fd7026"}
})


myvpcsecuritygroup = t.add_resource(SecurityGroup(
    "myVPCSecurityGroup",
    GroupDescription="Security group for RDS DB Instance.",
    VpcId=Ref(vpcid)
))


instance_sg = t.add_resource(
    ec2.SecurityGroup(
        "InstanceSecurityGroup",
        GroupDescription="Enable SSH and HTTP access on the inbound port",
        SecurityGroupIngress=[
            ec2.SecurityGroupRule(
                IpProtocol="tcp",
                FromPort="22",
                ToPort="22",
                CidrIp=Ref(subnet),
            ),
            ec2.SecurityGroupRule(
                IpProtocol="tcp",
                FromPort="8080",
                ToPort="8080",
                CidrIp=Ref(subnet),
            ),
            ec2.SecurityGroupRule(
                IpProtocol="tcp",
                FromPort="8000",
                ToPort="8000",
                CidrIp=Ref(subnet),
            ),
            ec2.SecurityGroupRule(
                IpProtocol="tcp",
                FromPort="80",
                ToPort="80",
                CidrIp=Ref(subnet),
            ),
            ec2.SecurityGroupRule(
                IpProtocol="tcp",
                FromPort="443",
                ToPort="443",
                CidrIp=Ref(subnet),
            ),
            ec2.SecurityGroupRule(
                Description="Range for Inbound cellular devices. limit this range to the number of devices you have",
                IpProtocol="tcp",
                FromPort="40000",
                ToPort="65000",
                CidrIp="0.0.0.0/0",
            ),
        ]
    )
)


s3bucket = t.add_resource(Bucket("S3Bucket", AccessControl=AuthenticatedRead))

ec2_instance = t.add_resource(ec2.Instance(
    "Ec2Instance",
    ImageId=FindInMap("RegionMap", Ref("AWS::Region"), "AMI"),
    InstanceType="t3a.medium",
    KeyName=Ref(keyname_param),
    SecurityGroups=[Ref(instance_sg)],
    UserData=Base64("80")
))


dbname = t.add_parameter(Parameter(
    "DBName",
    Default="MetrollaDB",
    Description="The database name",
    Type="String",
    MinLength="1",
    MaxLength="64",
    AllowedPattern="[a-zA-Z][a-zA-Z0-9]*",
    ConstraintDescription=("must begin with a letter and contain only"
                           " alphanumeric characters.")
))

dbuser = t.add_parameter(Parameter(
    "DBUser",
    NoEcho=True,
    Description="The database admin account username",
    Type="String",
    MinLength="1",
    MaxLength="16",
    AllowedPattern="[a-zA-Z][a-zA-Z0-9]*",
    ConstraintDescription=("must begin with a letter and contain only"
                           " alphanumeric characters.")
))

dbpassword = t.add_parameter(Parameter(
    "DBPassword",
    NoEcho=True,
    Description="The database admin account password",
    Type="String",
    MinLength="1",
    MaxLength="41",
    AllowedPattern="[a-zA-Z0-9]*",
    ConstraintDescription="must contain only alphanumeric characters."
))

dbclass = t.add_parameter(Parameter(
    "DBClass",
    Default="db.m1.small",
    Description="Database instance class",
    Type="String",
    AllowedValues=["db.t2.small", "db.t2.medium", "db.t2.large"],
    ConstraintDescription="must select a valid database instance type.",
))

dballocatedstorage = t.add_parameter(Parameter(
    "DBAllocatedStorage",
    Default="8",
    Description="The size of the database (Gb)",
    Type="Number",
    MinValue="5",
    MaxValue="1024",
    ConstraintDescription="must be between 5 and 1024Gb.",
))

mydbsubnetgroup = t.add_resource(DBSubnetGroup(
    "MyDBSubnetGroup",
    DBSubnetGroupDescription="Subnets available for the RDS DB Instance",
    SubnetIds=Ref(subnet),
))


mydb = t.add_resource(DBInstance(
    "MyDB",
    DBName=Ref(dbname),
    AllocatedStorage=Ref(dballocatedstorage),
    DBInstanceClass=Ref(dbclass),
    Engine="postgres",
    MasterUsername=Ref(dbuser),
    MasterUserPassword=Ref(dbpassword),
    DBSubnetGroupName=Ref(mydbsubnetgroup),
    VPCSecurityGroups=[Ref(myvpcsecuritygroup)],
))


with open('../Cloudformation/metrolla.cft', 'w+') as file:
    file.write(t.to_json())

