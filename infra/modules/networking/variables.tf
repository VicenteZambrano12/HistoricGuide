variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "vpc_name" {
  type    = string
  default = "portfolio-vpc"
}

variable "qdrant_subnet_cidr" {
  type    = string
  default = "10.0.1.0/24"
}

variable "serverless_subnet_cidr" {
  type    = string
  default = "10.0.2.0/28"
}

variable "common_labels" {
  type = map(string)
}
