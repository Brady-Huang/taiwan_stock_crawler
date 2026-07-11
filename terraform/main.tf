terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_compute_network" "vpc" {
  name                    = "taiwan-stock-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "taiwan-stock-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc.id
}

resource "google_compute_firewall" "allow_ports" {
  name    = "taiwan-stock-allow-ports"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["22", "8000", "8080", "5555", "8888", "3306"]
  }

  source_ranges = ["0.0.0.0/0"]
}

resource "google_compute_address" "static_ip" {
  name   = "taiwan-stock-ip"
  region = var.region
}

resource "google_compute_instance" "vm" {
  name         = "taiwan-stock-vm"
  machine_type = var.machine_type
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = 50
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.subnet.id
    access_config {
      nat_ip = google_compute_address.static_ip.address
    }
  }

  metadata_startup_script = templatefile("${path.module}/startup.sh", {
    repo_url = "https://github.com/Brady-Huang/taiwan_stock_crawler.git"
  })

  tags = ["taiwan-stock"]
}