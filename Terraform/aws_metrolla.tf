terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
}

##################################################################
# Data sources to get VPC, subnet, security group and AMI details
##################################################################
resource "aws_default_subnet" "default_az1" {
  availability_zone = "us-west-2a"

  tags = {
    Name = "Default subnet for us-west-2a"
  }
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnet_ids" "all" {
  vpc_id = data.aws_vpc.default.id
}

module "security_group" {
  source  = "terraform-aws-modules/security-group/aws"
  version = "~> 3.0"

  name        = "Metrolla"
  description = "Security group for example usage with EC2 instance"
  vpc_id      = data.aws_vpc.default.id

  ingress_cidr_blocks = [data.aws_vpc.default.cidr_block]
  ingress_rules       = ["http-80-tcp", "https-443-tcp"]
  egress_rules        = ["all-all"]
}

resource "aws_security_group_rule" "device-ports" {
  type              = "ingress"
  from_port         = 40000
  to_port           = 65535
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = module.security_group.this_security_group_id
}

resource "aws_security_group_rule" "web-ports" {
  type              = "ingress"
  from_port         = 8000
  to_port           = 8000
  protocol          = "tcp"
  cidr_blocks       = [data.aws_vpc.default.cidr_block]
  security_group_id = module.security_group.this_security_group_id
}

resource "aws_security_group_rule" "app-ports" {
  type              = "ingress"
  from_port         = 8080
  to_port           = 8080
  protocol          = "tcp"
  cidr_blocks       = [data.aws_vpc.default.cidr_block]
  security_group_id = module.security_group.this_security_group_id
}

resource "aws_network_interface" "this" {
  count = 1
  subnet_id = tolist(data.aws_subnet_ids.all.ids)[count.index]
}

resource "aws_instance" "web" {
  ami           = "ami-0a634ae95e11c6f91"
  instance_type = "t3.micro"
  subnet_id     = tolist(data.aws_subnet_ids.all.ids)[0]
  vpc_security_group_ids      = [module.security_group.this_security_group_id]
  associate_public_ip_address = true

  tags = {
    Name = "Metrolla"
  }
}

resource "aws_s3_bucket" "b" {
  bucket = "metrolla-data"
  acl = "private"

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    expose_headers = [
      "ETag",
      "Content-Type",
      "Accept-Ranges",
      "Content-Length"]
  }
}


resource "aws_db_subnet_group" "default" {
  name       = "main"
  subnet_ids = tolist(data.aws_subnet_ids.all.ids)

  tags = {
    Name = "My subnet group"
  }
}

resource "aws_db_instance" "metrolla" {
  allocated_storage    = 20
  storage_type         = "gp2"
  engine               = "postgres"
  instance_class       = "db.t2.micro"
  name                 = "metrolla"
  username             = "MetrollaAdmin"
  password             = "Metrolla01!"
  db_subnet_group_name = aws_db_subnet_group.default.name
}