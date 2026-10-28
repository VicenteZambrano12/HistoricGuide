terraform {
  backend "gcs" {
    bucket = "terraform_bucket_portfolio"
    prefix = "historic_guide/prod"
  }
}
