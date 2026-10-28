output "vpc_id" {
  value = data.google_compute_network.default.id
}

output "qdrant_subnet_id" {
  value = google_compute_subnetwork.qdrant.id
}

output "serverless_subnet_id" {
  value = google_compute_subnetwork.serverless_egress.id
}
