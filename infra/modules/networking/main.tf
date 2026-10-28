data "google_compute_network" "default" {
  project = var.project_id
  name    = var.vpc_name
}

resource "google_compute_subnetwork" "qdrant" {
  project                  = var.project_id
  name                     = "qdrant-subnet"
  region                   = var.region
  network                  = data.google_compute_network.default.id
  ip_cidr_range            = var.qdrant_subnet_cidr
  private_ip_google_access = true
}

resource "google_compute_subnetwork" "serverless_egress" {
  project                  = var.project_id
  name                     = "serverless-egress-subnet"
  region                   = var.region
  network                  = data.google_compute_network.default.id
  ip_cidr_range            = var.serverless_subnet_cidr
  private_ip_google_access = true
}

resource "google_compute_router" "default" {
  project = var.project_id
  name    = "qdrant-router"
  region  = var.region
  network = data.google_compute_network.default.id
}

# NAT scoped only to the qdrant-subnet so it can pull Docker images from the internet
resource "google_compute_router_nat" "qdrant" {
  project                            = var.project_id
  name                               = "qdrant-nat"
  router                             = google_compute_router.default.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "LIST_OF_SUBNETWORKS"

  subnetwork {
    name                    = google_compute_subnetwork.qdrant.id
    source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
  }
}

resource "google_compute_firewall" "allow_ssh_iap" {
  project       = var.project_id
  name          = "allow-ssh-iap"
  network       = data.google_compute_network.default.id
  direction     = "INGRESS"
  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["qdrant-vm"]

  allow {
  protocol = "tcp"
  ports    = ["22", "6333"]
}
}

resource "google_compute_firewall" "allow_cloud_run_to_qdrant" {
  project       = var.project_id
  name          = "allow-cloud-run-to-qdrant"
  network       = data.google_compute_network.default.id
  direction     = "INGRESS"
  source_ranges = [var.serverless_subnet_cidr]
  target_tags   = ["qdrant-vm"]

  allow {
    protocol = "tcp"
    ports    = ["6333"]
  }
}
